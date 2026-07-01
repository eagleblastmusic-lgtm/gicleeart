--[[
  json.lua — minimal JSON encoder/decoder for Lua 5.1
  Copyright (c) 2020 rxi (MIT) — https://github.com/rxi/json.lua
]]

local json = { _version = "0.1.2" }

local encode

local escape_char_map = {
  ["\\"] = "\\",
  ["\""] = "\"",
  ["\b"] = "b",
  ["\f"] = "f",
  ["\n"] = "n",
  ["\r"] = "r",
  ["\t"] = "t",
}

local escape_char_map_inv = { ["/"] = "/" }
for k, v in pairs(escape_char_map) do
  escape_char_map_inv[v] = k
end

local function escape_char(c)
  return "\\" .. (escape_char_map[c] or string.format("u%04x", c:byte()))
end

local function encode_nil(val)
  return "null"
end

local function encode_table(val, stack)
  local res = {}
  stack = stack or {}

  if stack[val] then error("circular reference") end
  stack[val] = true

  if rawget(val, 1) ~= nil or next(val) == nil then
    local n = 0
    for k in pairs(val) do
      if type(k) ~= "number" then
        error("invalid table: mixed or invalid key types")
      end
      n = n + 1
    end
    if n ~= #val then
      error("invalid table: sparse array")
    end
    for i, v in ipairs(val) do
      table.insert(res, encode(v, stack))
    end
    stack[val] = nil
    return "[" .. table.concat(res, ",") .. "]"
  else
    for k, v in pairs(val) do
      if type(k) ~= "string" then
        error("invalid table: mixed or invalid key types")
      end
      table.insert(res, encode(k, stack) .. ":" .. encode(v, stack))
    end
    stack[val] = nil
    return "{" .. table.concat(res, ",") .. "}"
  end
end

local function encode_string(val)
  return '"' .. val:gsub('[%z\\"\b\f\n\r\t]', escape_char) .. '"'
end

local function encode_number(val)
  if val ~= val or val <= -math.huge or val >= math.huge then
    return "null"
  end
  return string.format("%.14g", val)
end

local type_func_map = {
  ["nil"] = encode_nil,
  ["table"] = encode_table,
  ["string"] = encode_string,
  ["number"] = encode_number,
  ["boolean"] = tostring,
}

encode = function(val, stack)
  local t = type(val)
  local f = type_func_map[t]
  if f then
    return f(val, stack)
  end
  error("unexpected type '" .. t .. "'")
end

function json.encode(val)
  return (encode(val))
end

local parse

local function create_set(...)
  local res = {}
  for i = 1, select("#", ...) do
    res[select(i, ...)] = true
  end
  return res
end

local space_chars = create_set(" ", "\t", "\r", "\n")
local delim_chars = create_set(" ", "\t", "\r", "\n", "]", "}", ",")
local escape_chars = create_set("\\", "/", '"', "b", "f", "n", "r", "t", "u")
local literals = create_set("true", "false", "null")

local function next_char(str, idx, set, negate)
  for i = idx, #str do
    if set[str:sub(i, i)] ~= negate then
      return i
    end
  end
  return #str + 1
end

local function decode_error(str, idx, msg)
  error(string.format("%s at position %d", msg, idx))
end

local function codepoint_to_utf8(n)
  local f = math.floor
  if n <= 0x7f then
    return string.char(n)
  elseif n <= 0x7ff then
    return string.char(f(n / 64) + 192, n % 64 + 128)
  elseif n <= 0xffff then
    return string.char(f(n / 4096) + 224, f(n % 4096 / 64) + 128, n % 64 + 128)
  elseif n <= 0x10ffff then
    return string.char(f(n / 262144) + 240, f(n % 262144 / 4096) + 128, f(n % 4096 / 64) + 128, n % 64 + 128)
  end
  error(string.format("invalid unicode codepoint '%x'", n))
end

local function parse_unicode_escape(s)
  local n1 = tonumber(s:sub(1, 4), 16)
  local n2 = tonumber(s:sub(7, 10), 16)
  if n2 then
    return codepoint_to_utf8((n1 - 0xd800) * 0x400 + (n2 - 0xdc00) + 0x10000)
  else
    return codepoint_to_utf8(n1)
  end
end

local function parse_string(str, i)
  local res = ""
  local j = i + 1
  while j <= #str do
    local x = str:byte(j)
    if x == 34 then
      return res, j + 1
    end
    if x == 92 then
      local c = str:sub(j + 1, j + 1)
      j = j + 2
      if c == "u" then
        local hex = str:match("^[dD][89aAbB]%x%x\\u%x%x%x%x", j)
        if hex then
          res = res .. parse_unicode_escape(hex)
          j = j + #hex
        else
          hex = str:match("^%x%x%x%x", j) or decode_error(str, j, "invalid unicode escape")
          res = res .. codepoint_to_utf8(tonumber(hex, 16))
          j = j + 4
        end
      else
        if not escape_chars[c] then
          decode_error(str, j - 1, "invalid escape char '" .. c .. "'")
        end
        res = res .. escape_char_map_inv[c]
      end
    else
      res = res .. str:sub(j, j)
      j = j + 1
    end
  end
  decode_error(str, i, "expected closing quote for string")
end

local function parse_number(str, i)
  local x = next_char(str, i, delim_chars)
  local s = str:sub(i, x - 1)
  local n = tonumber(s)
  if not n then
    decode_error(str, i, "invalid number '" .. s .. "'")
  end
  return n, x
end

local function parse_literal(str, i)
  local x = next_char(str, i, delim_chars)
  local word = str:sub(i, x - 1)
  if not literals[word] then
    decode_error(str, i, "invalid literal '" .. word .. "'")
  end
  if word == "true" then
    return true, x
  elseif word == "false" then
    return false, x
  elseif word == "null" then
    return nil, x
  end
end

local function parse_array(str, i)
  local res = {}
  local n = 1
  i = i + 1
  while 1 do
    i = next_char(str, i)
    local curr = str:sub(i, i)
    if curr == "]" then
      return res, i + 1
    end
    local val
    val, i = parse(str, i)
    res[n] = val
    n = n + 1
    i = next_char(str, i)
    curr = str:sub(i, i)
    if curr == "]" then
      return res, i + 1
    end
    if curr ~= "," then
      decode_error(str, i, "expected ']' or ','")
    end
  end
end

local function parse_object(str, i)
  local res = {}
  i = i + 1
  while 1 do
    i = next_char(str, i)
    local curr = str:sub(i, i)
    if curr == "}" then
      return res, i + 1
    end
    if curr ~= '"' then
      decode_error(str, i, "expected string for key")
    end
    local key
    key, i = parse(str, i)
    i = next_char(str, i)
    if str:sub(i, i) ~= ":" then
      decode_error(str, i, "expected ':' after key")
    end
    i = next_char(str, i + 1)
    local val
    val, i = parse(str, i)
    res[key] = val
    i = next_char(str, i)
    curr = str:sub(i, i)
    if curr == "}" then
      return res, i + 1
    end
    if curr ~= "," then
      decode_error(str, i, "expected '}' or ','")
    end
  end
end

parse = function(str, idx)
  local chr = str:sub(idx, idx)
  if chr == '"' then
    return parse_string(str, idx)
  elseif chr == "{" then
    return parse_object(str, idx)
  elseif chr == "[" then
    return parse_array(str, idx)
  elseif chr == "-" or chr:match("%d") then
    return parse_number(str, idx)
  else
    return parse_literal(str, idx)
  end
end

function json.decode(str)
  if type(str) ~= "string" then
    error("expected string")
  end
  local res, idx = parse(str, next_char(str, 1, space_chars, true))
  idx = next_char(str, idx, space_chars, true)
  if idx <= #str then
    decode_error(str, idx, "trailing garbage")
  end
  return res
end

return json

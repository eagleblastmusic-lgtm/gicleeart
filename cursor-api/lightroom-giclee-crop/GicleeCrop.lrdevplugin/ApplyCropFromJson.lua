--[[
  Giclée — ustawia kadrowanie Develop wg pliku „Dane kadrowania.json”
  (ten sam format co crop.json z mockupu własnej fotografii).
]]

local LrApplication = import "LrApplication"
local LrApplicationView = import "LrApplicationView"
local LrDevelopController = import "LrDevelopController"
local LrDialogs = import "LrDialogs"
local LrFileUtils = import "LrFileUtils"
local LrPathUtils = import "LrPathUtils"
local LrProgressScope = import "LrProgressScope"
local LrTasks = import "LrTasks"

local JSON = dofile(LrPathUtils.child(_PLUGIN.path, "json.lua"))

local CROP_JSON_NAMES = {
  "Dane kadrowania.json",
  "crop.json",
}

local PREVIEW_HINTS = {
  "mockup",
  "podgląd",
  "podglad",
  "preview",
}

local function trim(s)
  return (s or ""):match("^%s*(.-)%s*$") or ""
end

local function lower(s)
  return string.lower(s or "")
end

local function looksLikePreview(fileName)
  local name = lower(fileName)
  for _, hint in ipairs(PREVIEW_HINTS) do
    if name:find(hint, 1, true) then
      return true
    end
  end
  return false
end

local function findCropJsonPath(photoPath)
  if not photoPath or photoPath == "" then
    return nil
  end
  local dir = LrPathUtils.parent(photoPath)
  if not dir then
    return nil
  end
  for _, name in ipairs(CROP_JSON_NAMES) do
    local candidate = LrPathUtils.child(dir, name)
    if LrFileUtils.exists(candidate) then
      return candidate
    end
  end
  return nil
end

local function readCropData(jsonPath)
  local raw = LrFileUtils.readFile(jsonPath)
  if not raw or raw == "" then
    return nil, "Plik JSON jest pusty"
  end
  local ok, data = pcall(JSON.decode, raw)
  if not ok or type(data) ~= "table" then
    return nil, "Nieprawidłowy JSON: " .. tostring(data)
  end
  local crop = data.cropSource
  if type(crop) ~= "table" then
    return nil, "Brak pola cropSource w JSON"
  end
  local x = tonumber(crop.x)
  local y = tonumber(crop.y)
  local w = tonumber(crop.width)
  local h = tonumber(crop.height)
  if not x or not y or not w or not h or w <= 0 or h <= 0 then
    return nil, "Nieprawidłowe współrzędne cropSource"
  end
  local srcW = tonumber(data.sourceWidthPx)
  local srcH = tonumber(data.sourceHeightPx)
  if not srcW or not srcH or srcW <= 0 or srcH <= 0 then
    return nil, "Brak sourceWidthPx / sourceHeightPx w JSON"
  end
  return {
    x = x,
    y = y,
    width = w,
    height = h,
    sourceWidthPx = srcW,
    sourceHeightPx = srcH,
    orientation = data.orientation,
  }, nil
end

local function clamp01(v)
  if v < 0 then
    return 0
  end
  if v > 1 then
    return 1
  end
  return v
end

local function computeNormalizedCrop(cropData, photoW, photoH)
  local scaleX = photoW / cropData.sourceWidthPx
  local scaleY = photoH / cropData.sourceHeightPx
  local mismatch = math.abs(scaleX - scaleY)

  local x = cropData.x * scaleX
  local y = cropData.y * scaleY
  local w = cropData.width * scaleX
  local h = cropData.height * scaleY

  local cropLeft = clamp01(x / photoW)
  local cropTop = clamp01(y / photoH)
  local cropRight = clamp01((x + w) / photoW)
  local cropBottom = clamp01((y + h) / photoH)

  if cropRight <= cropLeft or cropBottom <= cropTop then
    return nil, "Wyliczone kadrowanie ma zerowy obszar"
  end

  local note = nil
  if mismatch > 0.03 then
    note = string.format(
      "Uwaga: proporcje pliku (%.0f×%.0f) różnią się od JSON (%.0f×%.0f) — kadrowanie przeskalowane osobno w X i Y.",
      photoW,
      photoH,
      cropData.sourceWidthPx,
      cropData.sourceHeightPx
    )
  end

  return {
    left = cropLeft,
    top = cropTop,
    right = cropRight,
    bottom = cropBottom,
    note = note,
  }, nil
end

local function applyCropToPhoto(catalog, photo, cropLeft, cropTop, cropRight, cropBottom)
  local inDevelop = LrApplicationView.getCurrentModuleName() == "develop"
  local isTarget = photo == catalog:getTargetPhoto()

  if inDevelop and isTarget then
    LrDevelopController.setValue("CropConstrainAspectRatio", false)
    LrDevelopController.setValue("straightenAngle", 0)
    LrDevelopController.setValue("CropLeft", cropLeft)
    LrDevelopController.setValue("CropRight", cropRight)
    LrDevelopController.setValue("CropTop", cropTop)
    LrDevelopController.setValue("CropBottom", cropBottom)
  else
    photo:applyDevelopSettings({
      CropConstrainAspectRatio = false,
      CropLeft = cropLeft,
      CropRight = cropRight,
      CropTop = cropTop,
      CropBottom = cropBottom,
      CropAngle = 0,
    })
  end
end

local function processPhoto(catalog, photo)
  local fileName = photo:getFormattedMetadata("fileName") or "?"
  local photoPath = photo:getRawMetadata("path")
  if not photoPath or photoPath == "" then
    return false, fileName .. ": brak ścieżki pliku (zdjęcie może nie być lokalne)"
  end

  if looksLikePreview(fileName) then
    return false, fileName .. ": to wygląda na podgląd/mockup — zaznacz „Oryginał zdjęcia klienta”"
  end

  local jsonPath = findCropJsonPath(photoPath)
  if not jsonPath then
    return false, fileName .. ": brak „Dane kadrowania.json” w folderze zdjęcia"
  end

  local cropData, err = readCropData(jsonPath)
  if not cropData then
    return false, fileName .. ": " .. err
  end

  local photoW = photo:getRawMetadata("width")
  local photoH = photo:getRawMetadata("height")
  if not photoW or not photoH or photoW <= 0 or photoH <= 0 then
    return false, fileName .. ": nie można odczytać wymiarów zdjęcia"
  end

  local norm, normErr = computeNormalizedCrop(cropData, photoW, photoH)
  if not norm then
    return false, fileName .. ": " .. normErr
  end

  applyCropToPhoto(catalog, photo, norm.left, norm.top, norm.right, norm.bottom)

  local msg = fileName .. ": kadrowanie zastosowane"
  if norm.note then
    msg = msg .. " (" .. norm.note .. ")"
  end
  return true, msg
end

LrTasks.startAsyncTask(function()
  local catalog = LrApplication.activeCatalog()
  local photos = catalog:getTargetPhotos()

  if not photos or #photos == 0 then
    LrDialogs.message(
      "Giclée kadrowanie",
      "Zaznacz co najmniej jedno zdjęcie (najlepiej „Oryginał zdjęcia klienta.jpg” w folderze zamówienia)."
    )
    return
  end

  local okCount = 0
  local failCount = 0
  local messages = {}

  local progress = LrProgressScope({
    title = "Giclée — kadrowanie z JSON",
    caption = "Przygotowanie…",
  })

  catalog:withWriteAccessDo("Giclée — kadrowanie z JSON", function()
    for i, photo in ipairs(photos) do
      progress:setPortionComplete(i - 1, #photos)
      progress:setCaption((photo:getFormattedMetadata("fileName") or "?") .. "…")

      local ok, msg = processPhoto(catalog, photo)
      table.insert(messages, msg)
      if ok then
        okCount = okCount + 1
      else
        failCount = failCount + 1
      end
    end
  end)

  progress:done()

  local summary = string.format("Zastosowano: %d\nPominięto / błąd: %d", okCount, failCount)
  if #messages > 0 then
    local detail = table.concat(messages, "\n")
    if #detail > 3500 then
      detail = detail:sub(1, 3500) .. "\n…"
    end
    summary = summary .. "\n\n" .. detail
  end

  LrDialogs.message("Giclée kadrowanie", summary)
end)

--[[
  Giclée — ustawia kadrowanie Develop wg pliku „Dane kadrowania.json”
  (ten sam format co crop.json z mockupu własnej fotografii).
]]

local LrApplication = import "LrApplication"
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

local function extractIndexSuffix(fileName)
  local stem = fileName:match("^(.+)%.[^%.]+$") or fileName
  local index = stem:match("_(%d+)$")
  if index then
    return index
  end
  return nil
end

local function cropJsonCandidates(fileName)
  local names = {}
  local index = extractIndexSuffix(fileName)
  if index then
    table.insert(names, "Dane kadrowania_" .. index .. ".json")
    table.insert(names, "crop_" .. index .. ".json")
  end
  for _, name in ipairs(CROP_JSON_NAMES) do
    table.insert(names, name)
  end
  return names
end

local function findCropJsonPath(photoPath)
  if not photoPath or photoPath == "" then
    return nil
  end
  local dir = LrPathUtils.parent(photoPath)
  if not dir then
    return nil
  end
  local fileName = LrPathUtils.leafName(photoPath) or ""
  for _, name in ipairs(cropJsonCandidates(fileName)) do
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
  -- UTF-8 BOM (czesto po zapisie z Windows / R2)
  if raw:byte(1) == 0xEF and raw:byte(2) == 0xBB and raw:byte(3) == 0xBF then
    raw = raw:sub(4)
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

  local result = {
    x = x,
    y = y,
    width = w,
    height = h,
    sourceWidthPx = srcW,
    sourceHeightPx = srcH,
    orientation = data.orientation,
    frameConfig = data.frameConfig,
  }

  local display = data.cropSourceDisplay
  if type(display) == "table" then
    local dx = tonumber(display.x)
    local dy = tonumber(display.y)
    local dw = tonumber(display.width)
    local dh = tonumber(display.height)
    if dx and dy and dw and dh and dw > 0 and dh > 0 then
      result.displayX = dx
      result.displayY = dy
      result.displayW = dw
      result.displayH = dh
    end
  end
  result.displayWidthPx = tonumber(data.displayWidthPx)
  result.displayHeightPx = tonumber(data.displayHeightPx)

  return result, nil
end

local A4_SQRT2 = 1.4142135623730951

local function resolveOrientation(cropData)
  local o = lower(cropData.orientation or "")
  if o == "portrait" or o == "landscape" then
    return o
  end
  local cfg = cropData.frameConfig
  if type(cfg) == "table" and cfg.orientation then
    o = lower(tostring(cfg.orientation))
    if o == "portrait" or o == "landscape" then
      return o
    end
  end
  if cropData.width / cropData.height >= 1 then
    return "landscape"
  end
  return "portrait"
end

local function a4WidthOverHeight(orientation)
  if orientation == "portrait" then
    return 1 / A4_SQRT2
  end
  return A4_SQRT2
end

local function pickSourceRect(cropData)
  if cropData.displayX and cropData.displayW and cropData.displayWidthPx and cropData.displayWidthPx > 0 then
    local toFullX = cropData.sourceWidthPx / cropData.displayWidthPx
    local dispH = cropData.displayHeightPx or cropData.displayWidthPx
    local toFullY = cropData.sourceHeightPx / dispH
    local toFull = (toFullX + toFullY) / 2
    return {
      x = cropData.displayX * toFull,
      y = cropData.displayY * toFull,
      width = cropData.displayW * toFull,
      height = cropData.displayH * toFull,
      via = "cropSourceDisplay",
    }
  end
  return {
    x = cropData.x,
    y = cropData.y,
    width = cropData.width,
    height = cropData.height,
    via = "cropSource",
  }
end

local function enforceA4Pixels(cx, cy, w, h, orientation)
  local target = a4WidthOverHeight(orientation)
  local nw, nh
  if w / h >= target then
    nh = h
    nw = h * target
  else
    nw = w
    nh = w / target
  end
  return cx - nw / 2, cy - nh / 2, nw, nh
end

local function clampRectToPhoto(x, y, w, h, photoW, photoH)
  if w > photoW then
    local s = photoW / w
    w = photoW
    h = h * s
  end
  if h > photoH then
    local s = photoH / h
    h = photoH
    w = w * s
  end
  if x < 0 then
    x = 0
  end
  if y < 0 then
    y = 0
  end
  if x + w > photoW then
    x = photoW - w
  end
  if y + h > photoH then
    y = photoH - h
  end
  if x < 0 then
    x = 0
  end
  if y < 0 then
    y = 0
  end
  return x, y, w, h
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
  local scale = (scaleX + scaleY) / 2
  local mismatch = math.abs(scaleX - scaleY)

  local rect = pickSourceRect(cropData)
  local x = rect.x * scale
  local y = rect.y * scale
  local w = rect.width * scale
  local h = rect.height * scale
  local cx = x + w / 2
  local cy = y + h / 2

  local orientation = resolveOrientation(cropData)
  x, y, w, h = enforceA4Pixels(cx, cy, w, h, orientation)
  x, y, w, h = clampRectToPhoto(x, y, w, h, photoW, photoH)

  local cropLeft = clamp01(x / photoW)
  local cropTop = clamp01(y / photoH)
  local cropRight = clamp01((x + w) / photoW)
  local cropBottom = clamp01((y + h) / photoH)

  if cropRight <= cropLeft or cropBottom <= cropTop then
    return nil, "Wyliczone kadrowanie ma zerowy obszar"
  end

  local appliedRatio = (cropRight - cropLeft) * photoW / ((cropBottom - cropTop) * photoH)
  local targetRatio = a4WidthOverHeight(orientation)
  local note = string.format(
    "A4 %s (%.3f), źródło: %s",
    orientation,
    appliedRatio,
    rect.via or "?"
  )
  if mismatch > 0.03 then
    note = note .. string.format(
      "; uwaga: plik %.0f×%.0f vs JSON %.0f×%.0f",
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
    aspectRatio = targetRatio,
    note = note,
  }, nil
end

local VIRTUAL_COPY_NAME = "Kadrowanie A4"
local CROPPED_LABEL_COLOR = "green"

local function resolveMasterPhoto(photo)
  if photo:getRawMetadata("isVirtualCopy") then
    return photo:getRawMetadata("masterPhoto") or photo
  end
  return photo
end

local function getCollectionsForPhoto(photo)
  local collections = photo:getContainedCollections()
  if not collections then
    return {}
  end
  return collections
end

local function applyCropToPhoto(catalog, photoUuid, norm)
  local target = catalog:findPhotoByUuid(photoUuid)
  if not target then
    error("Nie znaleziono kopii wirtualnej w katalogu")
  end
  if not target.applyDevelopSettings then
    error("Brak applyDevelopSettings w tej wersji Lightroom")
  end

  catalog:setSelectedPhotos(target, { target })
  local aspectStr = string.format("%.10f", norm.aspectRatio or A4_SQRT2)
  target:applyDevelopSettings({
    CropConstrainAspectRatio = aspectStr,
    CropLeft = norm.left,
    CropRight = norm.right,
    CropTop = norm.top,
    CropBottom = norm.bottom,
    CropAngle = 0,
  }, "Giclée A4")
  target:setRawMetadata("colorNameForLabel", CROPPED_LABEL_COLOR)
end

local function addPhotoToCollections(photo, collections)
  for _, collection in ipairs(collections) do
    collection:addPhotos({ photo })
  end
end

local function createVirtualCopyForCrop(catalog, masterPhoto)
  catalog:setSelectedPhotos(masterPhoto, { masterPhoto })
  local copies = catalog:createVirtualCopies(VIRTUAL_COPY_NAME)
  if copies and copies[1] then
    return copies[1]:getRawMetadata("uuid")
  end
  local target = catalog:getTargetPhoto()
  if target then
    return target:getRawMetadata("uuid")
  end
  return nil
end

local function prepareCropForPhoto(photo)
  local fileName = photo:getFormattedMetadata("fileName") or "?"
  local photoPath = photo:getRawMetadata("path")
  if not photoPath or photoPath == "" then
    return nil, fileName .. ": brak ścieżki pliku (zdjęcie może nie być lokalne)"
  end

  if looksLikePreview(fileName) then
    return nil, fileName .. ": to wygląda na podgląd/mockup — zaznacz „Oryginał zdjęcia klienta”"
  end

  local jsonPath = findCropJsonPath(photoPath)
  if not jsonPath then
    return nil, fileName .. ": brak pliku kadrowania (Dane kadrowania*.json) w folderze zdjęcia"
  end

  local cropData, err = readCropData(jsonPath)
  if not cropData then
    return nil, fileName .. ": " .. err
  end

  local photoW = photo:getRawMetadata("width")
  local photoH = photo:getRawMetadata("height")
  if not photoW or not photoH or photoW <= 0 or photoH <= 0 then
    return nil, fileName .. ": nie można odczytać wymiarów zdjęcia"
  end

  local norm, normErr = computeNormalizedCrop(cropData, photoW, photoH)
  if not norm then
    return nil, fileName .. ": " .. normErr
  end

  return {
    fileName = fileName,
    norm = norm,
  }, nil
end

local function processPhoto(catalog, photo)
  local prepared, prepErr = prepareCropForPhoto(photo)
  if not prepared then
    return false, prepErr
  end

  local masterPhoto = resolveMasterPhoto(photo)
  local collections = getCollectionsForPhoto(photo)
  local virtualCopyUuid = nil
  local createdNewCopy = false

  if photo:getRawMetadata("isVirtualCopy")
    and photo:getFormattedMetadata("copyName") == VIRTUAL_COPY_NAME then
    virtualCopyUuid = photo:getRawMetadata("uuid")
  else
    catalog:withWriteAccessDo("Giclée — kopia wirtualna", function()
      virtualCopyUuid = createVirtualCopyForCrop(catalog, masterPhoto)
    end)
    createdNewCopy = virtualCopyUuid ~= nil
  end

  if not virtualCopyUuid or virtualCopyUuid == "" then
    return false, prepared.fileName .. ": nie udało się utworzyć kopii wirtualnej"
  end

  catalog:withWriteAccessDo("Giclée — kadrowanie", function()
    local virtualCopy = catalog:findPhotoByUuid(virtualCopyUuid)
    if createdNewCopy and virtualCopy and #collections > 0 then
      addPhotoToCollections(virtualCopy, collections)
    end
    applyCropToPhoto(catalog, virtualCopyUuid, prepared.norm)
  end)

  local virtualCopy = catalog:findPhotoByUuid(virtualCopyUuid)
  local copyName = VIRTUAL_COPY_NAME
  if virtualCopy then
    copyName = virtualCopy:getFormattedMetadata("copyName") or VIRTUAL_COPY_NAME
  end
  local msg = prepared.fileName .. " → " .. copyName .. ": kadrowanie na kopii wirtualnej, etykieta zielona"
  if createdNewCopy and #collections > 0 then
    msg = msg .. ", dodano do " .. #collections .. " kolekcji"
  end
  if prepared.norm.note then
    msg = msg .. " (" .. prepared.norm.note .. ")"
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

  for i, photo in ipairs(photos) do
    progress:setPortionComplete(i - 1, #photos)
    progress:setCaption((photo:getFormattedMetadata("fileName") or "?") .. "…")

    local pcallOk, okOrErr, msgOrNil = LrTasks.pcall(function()
      return processPhoto(catalog, photo)
    end)
    local ok, msg
    if pcallOk then
      ok, msg = okOrErr, msgOrNil
    else
      ok = false
      msg = (photo:getFormattedMetadata("fileName") or "?") .. ": " .. tostring(okOrErr)
    end
    table.insert(messages, msg)
    if ok then
      okCount = okCount + 1
    else
      failCount = failCount + 1
    end
  end

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

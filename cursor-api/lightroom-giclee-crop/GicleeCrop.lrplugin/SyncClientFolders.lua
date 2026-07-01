--[[
  Giclee — synchronizacja folderow klientow z dysku do kolekcji LR.
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrFileUtils = import "LrFileUtils"
local LrPathUtils = import "LrPathUtils"
local LrProgressScope = import "LrProgressScope"
local LrTasks = import "LrTasks"

local CONFIG = dofile(LrPathUtils.child(_PLUGIN.path, "Config.lua"))
local JSON = dofile(LrPathUtils.child(_PLUGIN.path, "json.lua"))

local STATE_DIR = LrPathUtils.child(_PLUGIN.path, "data")
local STATE_FILE = LrPathUtils.child(STATE_DIR, "synced_client_folders.json")
local CONVERT_SCRIPT = LrPathUtils.child(_PLUGIN.path, "convert_for_lr.py")
local PLUGIN_VERSION = "1.3.6"

local function trim(s)
  return (s or ""):match("^%s*(.-)%s*$") or ""
end

local function toNativePath(path)
  path = LrPathUtils.standardizePath(path or "")
  if WIN_ENV then
    return path:gsub("/", "\\")
  end
  return path
end

local function pathKind(path)
  return LrFileUtils.exists(toNativePath(path))
end

local function isDirectory(path)
  local native = toNativePath(path)
  local kind = LrFileUtils.exists(native)
  if kind == "directory" then
    return true
  end
  if kind == "file" then
    return false
  end
  local attrs = LrFileUtils.fileAttributes(native)
  if attrs and next(attrs) ~= nil and attrs.fileSize == nil then
    return true
  end
  return false
end

local function resolveChildPath(rootPath, entry)
  local nativeRoot = toNativePath(rootPath)
  local text = trim(entry)
  if text == "" then
    return nativeRoot
  end
  text = toNativePath(text)
  if text:match("^[A-Za-z]:") or text:sub(1, 1) == "/" then
    return text
  end
  return toNativePath(LrPathUtils.child(nativeRoot, text))
end

local function loadState()
  if pathKind(STATE_FILE) ~= "file" then
    return { folders = {} }
  end
  local raw = LrFileUtils.readFile(toNativePath(STATE_FILE))
  if not raw or raw == "" then
    return { folders = {} }
  end
  local ok, data = pcall(JSON.decode, raw)
  if ok and type(data) == "table" and type(data.folders) == "table" then
    return data
  end
  return { folders = {} }
end

local function writeTextFile(path, contents)
  local native = toNativePath(path)
  local file, err = io.open(native, "wb")
  if not file then
    return false, err or "io.open failed"
  end
  file:write(contents or "")
  file:close()
  return true
end

local function saveState(state)
  if pathKind(STATE_DIR) ~= "directory" then
    LrFileUtils.createAllDirectories(toNativePath(STATE_DIR))
  end
  return writeTextFile(STATE_FILE, JSON.encode(state))
end

local function isOriginalFileName(name)
  local prefix = CONFIG.ORIGINAL_FILE_PREFIX or "Oryginał zdjęcia klienta"
  if not name or name == "" then
    return false
  end
  if name:sub(1, #prefix) == prefix then
    return true
  end
  return name:sub(1, 7):lower() == "orygina"
end

local function listDirsViaCmd(rootPath)
  local folders = {}
  if not WIN_ENV then
    return folders
  end
  local native = toNativePath(rootPath)
  local cmd = 'cmd /c dir /b /ad "' .. native .. '"'
  local handle = io.popen(cmd, "r")
  if not handle then
    return folders
  end
  for line in handle:lines() do
    local name = trim(line)
    if name ~= "" and name ~= "." and name ~= ".." then
      table.insert(folders, {
        name = name,
        path = toNativePath(LrPathUtils.child(native, name)),
      })
    end
  end
  handle:close()
  return folders
end

local function listClientFolders(rootPath)
  local folders = {}
  local seen = {}
  local nativeRoot = toNativePath(rootPath)

  if not isDirectory(nativeRoot) then
    return folders
  end

  local function addFolder(name, fullPath)
    if not name or name == "" or seen[name] then
      return
    end
    if isDirectory(fullPath) then
      seen[name] = true
      table.insert(folders, { name = name, path = fullPath })
    end
  end

  for entry in LrFileUtils.directoryEntries(nativeRoot) do
    local fullPath = resolveChildPath(nativeRoot, entry)
    addFolder(LrPathUtils.leafName(fullPath), fullPath)
  end

  if #folders == 0 then
    local viaCmd = listDirsViaCmd(nativeRoot)
    for _, item in ipairs(viaCmd) do
      addFolder(item.name, item.path)
    end
  end

  table.sort(folders, function(a, b)
    return a.name < b.name
  end)
  return folders
end

local function catalogPath(path)
  return LrPathUtils.standardizePath(toNativePath(path))
end

local ORIGINAL_EXTENSIONS = { "jpg", "jpeg", "png", "heic", "tif", "tiff", "webp" }

local function findOriginalByExtensionProbe(folderPath)
  local nativeFolder = toNativePath(folderPath)
  local prefix = CONFIG.ORIGINAL_FILE_PREFIX or "Oryginał zdjęcia klienta"
  for _, ext in ipairs(ORIGINAL_EXTENSIONS) do
    for _, variant in ipairs({ ext, ext:upper() }) do
      local name = prefix .. "." .. variant
      local candidate = toNativePath(LrPathUtils.child(nativeFolder, name))
      if pathKind(candidate) == "file" then
        return candidate, name
      end
    end
  end
  return nil, nil
end

local function findOriginalFiles(folderPath)
  local nativeFolder = toNativePath(folderPath)
  local found = {}
  local seen = {}

  local function consider(name, candidate)
    if isOriginalFileName(name) and pathKind(candidate) == "file" then
      local key = catalogPath(candidate)
      if not seen[key] then
        seen[key] = true
        table.insert(found, { path = candidate, name = name })
      end
    end
  end

  for entry in LrFileUtils.directoryEntries(nativeFolder) do
    local candidate = resolveChildPath(nativeFolder, entry)
    if pathKind(candidate) == "file" then
      consider(LrPathUtils.leafName(candidate), candidate)
    end
  end

  if #found == 0 then
    for entry in LrFileUtils.files(nativeFolder) do
      local candidate = resolveChildPath(nativeFolder, entry)
      consider(LrPathUtils.leafName(candidate), candidate)
    end
  end

  if #found == 0 then
    local probePath, probeName = findOriginalByExtensionProbe(folderPath)
    if probePath then
      table.insert(found, { path = probePath, name = probeName })
    end
  end

  table.sort(found, function(a, b)
    return a.name < b.name
  end)
  return found
end

local function findCollectionSetByName(catalog, name)
  for _, set in ipairs(catalog:getChildCollectionSets()) do
    if set:getName() == name then
      return set
    end
  end
  return nil
end

local function findCollectionInSet(set, name)
  for _, col in ipairs(set:getChildCollections()) do
    if col:getName() == name then
      return col
    end
  end
  return nil
end

local function photoInCollection(collection, photo)
  if not collection or not photo then
    return false
  end
  local photos = collection:getPhotos()
  if not photos then
    return false
  end
  for _, p in ipairs(photos) do
    if p == photo then
      return true
    end
  end
  return false
end

local function pathVariants(path)
  local native = toNativePath(path)
  local std = catalogPath(path)
  if native == std then
    return { native }
  end
  return { native, std }
end

local function findPhotoInCatalog(catalog, filePath)
  for _, variant in ipairs(pathVariants(filePath)) do
    local photo = catalog:findPhotoByPath(variant, "caseInsensitive")
    if photo then
      return photo, variant
    end
  end
  return nil, nil
end

local function allImportPathVariants(filePath)
  local seen = {}
  local variants = {}
  local function add(path)
    if not path or path == "" or seen[path] then
      return
    end
    seen[path] = true
    if pathKind(path) == "file" then
      table.insert(variants, path)
    end
  end
  add(toNativePath(filePath))
  add(catalogPath(filePath))
  return variants
end

local function fileExtension(path)
  return (path:lower():match("%.([^%.\\/]+)$") or "")
end

local function needsJpegConversion(path)
  local ext = fileExtension(path)
  return ext == "webp" or ext == "heic" or ext == "heif"
end

local function shellQuote(path)
  return '"' .. toNativePath(path):gsub('"', '\\"') .. '"'
end

local function runShellCommand(cmd)
  if WIN_ENV then
    cmd = '"' .. cmd .. '"'
  end
  LrTasks.execute(cmd)
end

local function convertToJpegBesideOriginal(sourcePath)
  local native = toNativePath(sourcePath)
  if not needsJpegConversion(native) then
    return native, nil
  end

  local folder = LrPathUtils.parent(native)
  local leaf = LrPathUtils.leafName(native)
  local stem = leaf:match("^(.+)%.[^%.]+$") or leaf
  local dest = toNativePath(LrPathUtils.child(folder, stem .. ".jpg"))
  if pathKind(dest) == "file" then
    return dest, nil
  end

  if pathKind(CONVERT_SCRIPT) ~= "file" then
    return nil, "Brak skryptu convert_for_lr.py w wtyczce"
  end

  local cmd = string.format(
    "cmd /c python %s %s %s",
    shellQuote(CONVERT_SCRIPT),
    shellQuote(native),
    shellQuote(dest)
  )
  runShellCommand(cmd)

  if pathKind(dest) == "file" then
    return dest, nil
  end
  return nil, "Nie udało się przekonwertować " .. fileExtension(native) .. " → JPG (wymagany Python + Pillow)"
end

local function resolveImportPath(originalPath)
  local importPath, convertErr = convertToJpegBesideOriginal(originalPath)
  if importPath then
    return importPath, convertErr
  end
  return toNativePath(originalPath), convertErr
end

local function tryAddPhoto(catalog, filePath)
  local lastErr = nil
  for _, path in ipairs(allImportPathVariants(filePath)) do
    local photo = nil
    local ok, err = LrTasks.pcall(function()
      catalog:withWriteAccessDo("Giclée — import pliku", function()
        photo = catalog:addPhoto(path)
      end)
    end)
    if ok and photo then
      return photo, true, nil
    end
    if not ok then
      lastErr = err
    end
    photo = findPhotoInCatalog(catalog, path)
    if photo then
      return photo, true, nil
    end
  end
  return nil, false, lastErr
end

local function importOriginalPhoto(catalog, _folderPath, originalPath)
  local importPath, convertErr = resolveImportPath(originalPath)
  local photo = findPhotoInCatalog(catalog, importPath)
  if not photo and importPath ~= toNativePath(originalPath) then
    photo = findPhotoInCatalog(catalog, originalPath)
  end
  if photo then
    return photo, false, nil
  end
  if convertErr and pathKind(importPath) ~= "file" then
    return nil, false, convertErr
  end
  local importedPhoto, wasImported, importErr = tryAddPhoto(catalog, importPath)
  if importedPhoto then
    return importedPhoto, wasImported, importErr
  end
  if convertErr then
    importErr = convertErr .. (importErr and ("\n" .. tostring(importErr)) or "")
  end
  return nil, false, importErr
end

local function photoForOriginal(catalog, originalPath)
  local importPath = select(1, resolveImportPath(originalPath))
  local photo = findPhotoInCatalog(catalog, importPath)
  if not photo and importPath ~= toNativePath(originalPath) then
    photo = findPhotoInCatalog(catalog, originalPath)
  end
  return photo
end

local function folderFullySynced(catalog, clientSet, folder, folderPath)
  local originals = findOriginalFiles(folderPath)
  if #originals == 0 then
    return false
  end

  local collection = findCollectionInSet(clientSet, folder.name)
  if not collection then
    return false
  end

  for _, orig in ipairs(originals) do
    local photo = photoForOriginal(catalog, orig.path)
    if not photo or not photoInCollection(collection, photo) then
      return false
    end
  end
  return true
end

local function ensureCollection(catalog, clientSet, folderName)
  local collection = findCollectionInSet(clientSet, folderName)
  local justCreated = false
  if not collection then
    collection = catalog:createCollection(folderName, clientSet, true)
    justCreated = true
  end
  return collection, justCreated
end

local function addPhotoToCollection(catalog, clientSet, folder, photo, originalName, stats, lines, collection, justCreated)
  if not collection then
    stats.errors = stats.errors + 1
    table.insert(lines, folder.name .. ": błąd — nie udało się utworzyć kolekcji")
    return false
  end

  -- LR SDK: nie wolno wywołać getPhotos() na kolekcji utworzonej w tym samym withWriteAccessDo
  if justCreated or not photoInCollection(collection, photo) then
    collection:addPhotos({ photo })
    stats.addedToCollection = stats.addedToCollection + 1
    table.insert(lines, folder.name .. ": dodano " .. (originalName or "oryginał"))
    return true
  end
  return false
end

local function saveFolderState(state, folder, folderPath, originals)
  local saved = {}
  for _, orig in ipairs(originals) do
    table.insert(saved, {
      path = toNativePath(orig.path),
      name = orig.name,
    })
  end
  state.folders[folder.name] = {
    folderPath = folderPath,
    originals = saved,
    syncedAt = os.date("!%Y-%m-%dT%H:%M:%SZ"),
  }
end

LrTasks.startAsyncTask(function()
  local catalog = LrApplication.activeCatalog()
  local rootPath = toNativePath(CONFIG.CLIENT_ORDERS_DIR)
  local setName = CONFIG.COLLECTION_SET_NAME or "Zdjęcia klientów"

  if not isDirectory(rootPath) then
    LrDialogs.message(
      "Giclée — import klientów",
      "Nie znaleziono folderu:\n" .. rootPath .. "\n\nSprawdź Config.lua (CLIENT_ORDERS_DIR)."
    )
    return
  end

  local clientFolders = listClientFolders(rootPath)
  if #clientFolders == 0 then
    LrDialogs.message(
      "Giclée — import klientów",
      "Brak podfolderów w:\n" .. rootPath
        .. "\n\nWtyczka v"
        .. PLUGIN_VERSION
        .. " — jeśli foldery są widoczne w Explorerze, zrestartuj Lightroom i spróbuj ponownie."
    )
    return
  end

  local state = loadState()
  local stats = {
    scanned = #clientFolders,
    imported = 0,
    addedToCollection = 0,
    skipped = 0,
    noOriginal = 0,
    errors = 0,
  }
  local lines = {}

  local progress = LrProgressScope({
    title = "Giclée — import folderów klientów",
    caption = "Przygotowanie…",
  })

  local clientSet = nil
  catalog:withWriteAccessDo("Giclée — zestaw kolekcji klientów", function()
    clientSet = findCollectionSetByName(catalog, setName)
    if not clientSet then
      clientSet = catalog:createCollectionSet(setName, nil, true)
    end
  end)

  if not clientSet then
    progress:done()
    LrDialogs.message("Giclée — import klientów", "Nie udało się utworzyć zestawu kolekcji: " .. setName)
    return
  end

  for i, folder in ipairs(clientFolders) do
    progress:setPortionComplete(i - 1, #clientFolders)
    progress:setCaption(folder.name)

    local folderPath = toNativePath(folder.path)
    if folderFullySynced(catalog, clientSet, folder, folderPath) then
      stats.skipped = stats.skipped + 1
      table.insert(lines, folder.name .. ": już zsynchronizowane")
    else
      local originals = findOriginalFiles(folderPath)
      if #originals == 0 then
        stats.noOriginal = stats.noOriginal + 1
        table.insert(lines, folder.name .. ": brak pliku „" .. (CONFIG.ORIGINAL_FILE_PREFIX or "?") .. "”")
      else
        local syncedOriginals = {}
        local folderErrors = 0

        for _, orig in ipairs(originals) do
          local photo, wasImported, importErr = importOriginalPhoto(catalog, folderPath, orig.path)
          if not photo then
            folderErrors = folderErrors + 1
            local detail = folder.name
              .. ": nie udało się dodać do katalogu LR\n"
              .. toNativePath(orig.path)
            if importErr then
              detail = detail .. "\n" .. tostring(importErr)
            end
            table.insert(lines, detail)
          else
            if wasImported then
              stats.imported = stats.imported + 1
            end
            catalog:withWriteAccessDo("Giclée — kolekcja " .. folder.name, function()
              local collection, justCreated = ensureCollection(catalog, clientSet, folder.name)
              if addPhotoToCollection(
                catalog,
                clientSet,
                folder,
                photo,
                orig.name,
                stats,
                lines,
                collection,
                justCreated
              ) then
                table.insert(syncedOriginals, orig)
              elseif photoInCollection(collection, photo) then
                table.insert(syncedOriginals, orig)
              end
            end)
          end
        end

        if folderErrors > 0 then
          stats.errors = stats.errors + folderErrors
        end
        if #syncedOriginals > 0 then
          saveFolderState(state, folder, folderPath, syncedOriginals)
        end
      end
    end
  end

  local stateSaved, stateErr = saveState(state)
  progress:done()

  local summary = string.format(
    "Wtyczka v%s\nPrzeskanowano folderów: %d\nDodano do katalogu LR: %d\nDodano do kolekcji: %d\nPominięto: %d\nBez oryginału: %d\nBłędy: %d",
    PLUGIN_VERSION,
    stats.scanned,
    stats.imported,
    stats.addedToCollection,
    stats.skipped,
    stats.noOriginal,
    stats.errors
  )

  if not stateSaved then
    summary = summary .. "\n\nUwaga: nie zapisano stanu synchronizacji: " .. tostring(stateErr)
  end

  if #lines > 0 then
    local detail = table.concat(lines, "\n")
    if #detail > 3500 then
      detail = detail:sub(1, 3500) .. "\n…"
    end
    summary = summary .. "\n\n" .. detail
  end

  LrDialogs.message("Giclée — import klientów", summary)
end)

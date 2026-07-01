--[[
  Giclee - kadrowanie z pliku "Dane kadrowania.json"
  Instalacja: skopiuj folder GicleeCrop.lrplugin do
  %AppData%\Adobe\Lightroom\Modules\  i zrestartuj Lightroom Classic.
]]

return {
  VERSION = { major = 1, minor = 4, revision = 3 },

  LrSdkVersion = 10.0,
  LrSdkMinimumVersion = 3.0,
  LrToolkitIdentifier = "com.giclee.cropfromjson",
  LrPluginName = "Giclee Kadrowanie",
  LrPluginInfoUrl = "https://giclee.pl",

  -- Plik -> Dodatki do wtyczek (dziala we wszystkich modulach)
  LrExportMenuItems = {
    {
      title = "Zastosuj kadrowanie z JSON",
      file = "ApplyCropFromJson.lua",
      enabledWhen = "photosAvailable",
    },
    {
      title = "Importuj nowe foldery klientów",
      file = "SyncClientFolders.lua",
    },
  },

  -- Biblioteka -> Dodatki do wtyczek
  LrLibraryMenuItems = {
    {
      title = "Zastosuj kadrowanie z JSON",
      file = "ApplyCropFromJson.lua",
      enabledWhen = "photosAvailable",
    },
    {
      title = "Importuj nowe foldery klientów",
      file = "SyncClientFolders.lua",
    },
  },
}

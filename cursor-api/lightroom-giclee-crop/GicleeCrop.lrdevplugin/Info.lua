--[[
  Giclée — kadrowanie z pliku „Dane kadrowania.json” (format crop z mockupu sklepu).
  Instalacja: skopiuj folder GicleeCrop.lrdevplugin do
  %AppData%\Adobe\Lightroom\Modules\  i zrestartuj Lightroom Classic.
]]

return {
  LrSdkVersion = 6.0,
  LrSdkMinimumVersion = 3.0,
  LrToolkitIdentifier = "com.giclee.cropfromjson",
  LrPluginName = "Giclée Kadrowanie",
  LrPluginInfoUrl = "https://giclee.pl",

  LrLibraryMenuItems = {
    {
      title = "Zastosuj kadrowanie z JSON",
      file = "ApplyCropFromJson.lua",
    },
  },

  LrDevelopMenuItems = {
    {
      title = "Zastosuj kadrowanie z JSON",
      file = "ApplyCropFromJson.lua",
    },
  },
}

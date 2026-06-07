if not WeakAuras.IsLibsOK() then return end
---@type string
local AddonName = ...
---@class OptionsPrivate
local OptionsPrivate = select(2, ...)

if not WeakAuras.IsLibsOK() then return end
---@type string
local AddonName = ...
---@class OptionsPrivate
local OptionsPrivate = select(2, ...)
OptionsPrivate.changelog = {
  versionString = '5.21.1-1-g676ed8d2',
  dateString = '2026-01-23',
  fullChangeLogUrl = 'https://github.com/WeakAuras/WeakAuras2/compare/5.21.1...676ed8d20befb0a9c626278999637a44ce239671',
  commitText = [==[NoM0Re (1):

- Titan: add next phase encounter list

]==]
}
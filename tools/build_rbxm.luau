--[[
	Packs the Roblox scripts into assets/AnimeFace_Scripts.rbxm (run from the repo root):
		lune run tools/build_rbxm.luau
	Contents: AnimeFace (ModuleScript + Presets) -> ReplicatedStorage,
	          FaceSetup (Script) -> ServerScriptService,
	          FaceClient (LocalScript) -> StarterPlayer > StarterPlayerScripts.
]]
local fs = require("@lune/fs")
local roblox = require("@lune/roblox")
local Instance = roblox.Instance

local function script(class, name, path)
	local s = Instance.new(class)
	s.Name = name
	s.Source = fs.readFile(path)
	return s
end

local module = script("ModuleScript", "AnimeFace", "roblox/AnimeFace/init.lua")
script("ModuleScript", "Presets", "roblox/AnimeFace/Presets.lua").Parent = module
local server = script("Script", "FaceSetup", "roblox/FaceSetup.server.lua")
local client = script("LocalScript", "FaceClient", "roblox/FaceClient.client.lua")

local out = "assets/AnimeFace_Scripts.rbxm"
fs.writeFile(out, roblox.serializeModel({ module, server, client }))

-- read it back to make sure the file is valid and complete
local back = roblox.deserializeModel(fs.readFile(out))
local names = {}
for _, inst in back do
	table.insert(names, inst.ClassName .. ":" .. inst.Name)
	if inst.Name == "AnimeFace" then
		local p = inst:FindFirstChild("Presets")
		assert(p and p.Source == fs.readFile("roblox/AnimeFace/Presets.lua"), "Presets missing from rbxm")
		assert(inst.Source == fs.readFile("roblox/AnimeFace/init.lua"), "module source mismatch")
	end
end
print("wrote " .. out .. " -> " .. table.concat(names, ", "))

--[[
	FaceSetup (Script, ServerScriptService)

	Mounts the AnimeFace on every player's character and lets clients request expressions
	for their own face through a RemoteEvent. Requires in ReplicatedStorage:
		AnimeFace       (ModuleScript, with its Presets child)
		AnimeFaceModel  (the imported face model from AnimeFace.fbx, with its SurfaceAppearance)
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local AnimeFace = require(ReplicatedStorage:WaitForChild("AnimeFace"))
local template = ReplicatedStorage:WaitForChild("AnimeFaceModel")

-- nil = follow each avatar's head colour; set a Color3 to force a skin tone for everyone
local SKIN_COLOR = nil

local remote = ReplicatedStorage:FindFirstChild("AnimeFaceRemote") or Instance.new("RemoteEvent")
remote.Name = "AnimeFaceRemote"
remote.Parent = ReplicatedStorage

local lastRequest = {}

remote.OnServerEvent:Connect(function(player, action, value)
	local now = os.clock()
	if (lastRequest[player] or 0) > now - 0.1 then
		return
	end
	lastRequest[player] = now
	local character = player.Character
	if not character then
		return
	end
	if action == "Expression" and type(value) == "string" and AnimeFace.Presets.Expressions[value] then
		AnimeFace.setExpression(character, value)
	elseif action == "Blush" and type(value) == "number" then
		AnimeFace.setBlush(character, value)
	end
end)

local function onCharacter(character)
	local head = character:WaitForChild("Head", 10)
	if not head then
		return
	end
	AnimeFace.attach(character, template, { SkinColor = SKIN_COLOR })
end

local function onPlayer(player)
	player.CharacterAdded:Connect(onCharacter)
	if player.Character then
		onCharacter(player.Character)
	end
end

Players.PlayerAdded:Connect(onPlayer)
Players.PlayerRemoving:Connect(function(player)
	lastRequest[player] = nil
end)
for _, player in Players:GetPlayers() do
	onPlayer(player)
end

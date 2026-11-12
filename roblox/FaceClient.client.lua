--[[
	FaceClient (LocalScript, StarterPlayerScripts)

	Drives every AnimeFace this client can see: blinking, idle eye movement, expressions and blush
	from the server attributes, and mouth movement when that player chats (TextChatService).
	Set DEMO_KEYS to true to cycle your own expressions with "," and "." and toggle blush with "/".
]]

local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TextChatService = game:GetService("TextChatService")
local UserInputService = game:GetService("UserInputService")

local AnimeFace = require(ReplicatedStorage:WaitForChild("AnimeFace"))

local DEMO_KEYS = true

local controllers = {}

local function track(face)
	if controllers[face] or not face:IsDescendantOf(workspace) then
		return
	end
	controllers[face] = false -- pending
	task.spawn(function()
		if not AnimeFace.waitForRig(face, 15) then
			controllers[face] = nil
			return
		end
		local ok, ctrl = pcall(AnimeFace.new, face)
		if not ok then
			warn(ctrl)
			controllers[face] = nil
			return
		end
		if controllers[face] == nil then -- removed while waiting
			ctrl:Destroy()
			return
		end
		controllers[face] = ctrl:BindToAttributes()
	end)
end

local function untrack(face)
	local ctrl = controllers[face]
	controllers[face] = nil
	if ctrl then
		ctrl:Destroy()
	end
end

CollectionService:GetInstanceAddedSignal(AnimeFace.Tag):Connect(track)
CollectionService:GetInstanceRemovedSignal(AnimeFace.Tag):Connect(untrack)
for _, face in CollectionService:GetTagged(AnimeFace.Tag) do
	track(face)
end

local function controllerFor(player)
	local character = player and player.Character
	local face = character and character:FindFirstChild(AnimeFace.FaceName)
	return face and controllers[face] or nil
end

-- Talk when a player chats.
TextChatService.MessageReceived:Connect(function(message)
	local source = message.TextSource
	if not source then
		return
	end
	local ctrl = controllerFor(Players:GetPlayerByUserId(source.UserId))
	if ctrl then
		ctrl:Talk(message.Text)
	end
end)

if DEMO_KEYS then
	local remote = ReplicatedStorage:WaitForChild("AnimeFaceRemote")
	local order = AnimeFace.Presets.ExpressionOrder
	local mouths = {}
	for _, m in AnimeFace.Presets.Mouths do
		table.insert(mouths, m.Name)
	end
	local index, mouthIndex, blush = 1, 0, false
	UserInputService.InputBegan:Connect(function(input, processed)
		if processed then
			return
		end
		if input.KeyCode == Enum.KeyCode.Period or input.KeyCode == Enum.KeyCode.Comma then
			index = (index - 1 + (if input.KeyCode == Enum.KeyCode.Period then 1 else -1)) % #order + 1
			remote:FireServer("Expression", order[index])
			print("AnimeFace expression:", order[index])
		elseif input.KeyCode == Enum.KeyCode.M then
			-- cycle the 2D mouth images, then back to automatic (0)
			mouthIndex = (mouthIndex + 1) % (#mouths + 1)
			remote:FireServer("Mouth", mouths[mouthIndex])
			print("AnimeFace mouth:", mouths[mouthIndex] or "automatic")
		elseif input.KeyCode == Enum.KeyCode.Slash then
			blush = not blush
			remote:FireServer("Blush", if blush then 1 else 0)
		end
	end)
end

--[[
	Offline tests for the AnimeFace controller (run from the repo root):
		lune run tests/controller.test.luau

	Builds a fake imported rig whose axes are deliberately rotated (importer flips) and whose bones
	have random orientations, then checks that every expression moves each bone by exactly the
	intended head-space vector, and that attach() lands the face precisely on the Head.
]]
local fs = require("@lune/fs")
local luau = require("@lune/luau")
local roblox = require("@lune/roblox")

local Instance, CFrame, Vector3, Vector2, Color3 = roblox.Instance, roblox.CFrame, roblox.Vector3, roblox.Vector2, roblox.Color3

local fakeTime = 100
local steps = {}
local env = {
	game = {
		GetService = function(_, name)
			assert(name == "RunService", "unexpected service " .. name)
			return {
				PreSimulation = {
					Connect = function(_, fn)
						table.insert(steps, fn)
						return { Disconnect = function() end }
					end,
				},
			}
		end,
	},
	script = { WaitForChild = function(_, name) return name end },
	workspace = { CurrentCamera = nil },
	task = { wait = function() end },
	os = { clock = function() return fakeTime end },
	Instance = Instance, CFrame = CFrame, Vector3 = Vector3, Vector2 = Vector2,
	warn = function(...) print("[warn]", ...) end,
	typeof = typeof, math = math, string = string, table = table, pairs = pairs, ipairs = ipairs, next = next,
	type = type, tostring = tostring, tonumber = tonumber, setmetatable = setmetatable, getmetatable = getmetatable,
	assert = assert, error = error, pcall = pcall, select = select, print = print,
}
local Presets = luau.load(fs.readFile("roblox/AnimeFace/Presets.lua"), { debugName = "Presets" })()
env.require = function(x)
	assert(x == "Presets", "unexpected require " .. tostring(x))
	return Presets
end
local AnimeFace = luau.load(fs.readFile("roblox/AnimeFace/init.lua"), { debugName = "AnimeFace", environment = env })()

local failures, checks = 0, 0
local function check(cond, msg)
	checks += 1
	if not cond then
		failures += 1
		print("FAIL: " .. msg)
	end
end

local function rot(cf)
	return cf - cf.Position
end

-- deterministic pseudo-random rotations
local seed = 12345
local function rnd()
	seed = (seed * 1103515245 + 12345) % 2147483648
	return seed / 2147483648
end
local function randomRotation()
	return CFrame.Angles(rnd() * 6.283, rnd() * 6.283, rnd() * 6.283)
end

-- Q simulates whatever axis convention the importer ends up with (here: flipped 180 deg + tilted)
local Q = CFrame.Angles(0, math.pi, 0) * CFrame.Angles(0.3, 0.2, -0.1)
local P0 = CFrame.new(10, 5, -3) * CFrame.Angles(0.4, -1.1, 0.25)

local function buildTemplate()
	local model = Instance.new("Model")
	model.Name = "AnimeFaceModel"
	local part = Instance.new("MeshPart")
	part.Name = "AnimeFace"
	part.CFrame = P0
	part.Parent = model
	local world, inst = {}, {}
	for _, b in Presets.Bones do
		local p = b.Position
		local w = P0 * Q * CFrame.new(p[1], p[2], p[3]) * randomRotation()
		local bone = Instance.new("Bone")
		bone.Name = b.Name
		local parentWorld = if b.Parent then world[b.Parent] else P0
		bone.CFrame = parentWorld:Inverse() * w
		bone.Parent = if b.Parent then inst[b.Parent] else part
		world[b.Name], inst[b.Name] = w, bone
	end
	return model, part, world, inst
end

local function info(name)
	for _, b in Presets.Bones do
		if b.Name == name then
			return b
		end
	end
end

-- expected world displacement of a bone's own offset (independent re-derivation of the convention)
local function expectedWorld(name, off)
	local b = info(name)
	local side = if string.sub(name, -2) == "_L" then -1 elseif string.sub(name, -2) == "_R" then 1 else 1
	local T = Vector3.new(math.cos(b.Angle), 0, math.sin(b.Angle))
	local N = Vector3.new(math.sin(b.Angle), 0, -math.cos(b.Angle))
	local d = T * (off.X * side) + Vector3.new(0, off.Y, 0) + N * off.Z
	return rot(P0 * Q):VectorToWorldSpace(d)
end

local function actualWorld(world, inst, name)
	return rot(world[name]):VectorToWorldSpace(inst[name].Transform.Position)
end

local function step(seconds)
	local n = math.max(1, math.floor(seconds * 60))
	for _ = 1, n do
		fakeTime += 1 / 60
		for _, fn in steps do
			fn(1 / 60)
		end
	end
end

------------------------------------------------------------------ controller math
local template, part, world, inst = buildTemplate()
local ctrl = AnimeFace.new(template, { AutoBlink = false, AutoLook = false })
check(math.abs(ctrl.Scale - 1) < 1e-4, "scale should be 1, got " .. ctrl.Scale)

local tested, maxErr = 0, 0
for _, name in Presets.ExpressionOrder do
	if string.sub(name, 1, 4) ~= "Talk" then
		ctrl:SetExpression(name, 0.01)
		step(0.3)
		local offsets = Presets.Expressions[name].Offsets
		for _, b in Presets.Bones do
			local o = offsets[b.Name]
			local off = if o then Vector3.new(o[1], o[2], o[3]) else Vector3.new(0, 0, 0)
			local err = (actualWorld(world, inst, b.Name) - expectedWorld(b.Name, off)).Magnitude
			maxErr = math.max(maxErr, err)
			-- float32 CFrame maths ~10 studs from the origin: 5e-5 studs is noise, offsets are >= 2e-3
			check(err < 5e-5, string.format("%s/%s displacement error %.2e", name, b.Name, err))
		end
		tested += 1
	end
end
check(tested >= 20, "expected to test at least 20 expressions")
print(string.format("expressions tested: %d, max bone displacement error %.2e studs", tested, maxErr))

-- blink closes the lids to the Blink pose, then reopens
ctrl:SetExpression("Neutral", 0.01)
step(0.3)
ctrl:Blink()
step(0.1) -- inside the closed hold (0.07 s close + 0.04 s hold)
local closed = Presets.Expressions.Blink.Offsets.LidUpper_L
local lid = actualWorld(world, inst, "LidUpper_L")
local want = expectedWorld("LidUpper_L", Vector3.new(closed[1], closed[2], closed[3]))
check((lid - want).Magnitude < 2e-3, "blink should fully close LidUpper_L")
step(0.4)
check(actualWorld(world, inst, "LidUpper_L").Magnitude < 1e-4, "eyes should reopen after a blink")

-- no blinking during closed-eye expressions
ctrl:SetExpression("Happy", 0.01)
step(0.3)
local happyLid = actualWorld(world, inst, "LidUpper_R")
ctrl:Blink()
step(0.08)
check((actualWorld(world, inst, "LidUpper_R") - happyLid).Magnitude < 1e-6, "Happy eyes must not blink")

-- look right: both irises move toward the character's right
ctrl:SetExpression("Neutral", 0.01)
ctrl:SetLook(1, 0)
step(1)
local faceRight = rot(P0 * Q):VectorToWorldSpace(Vector3.new(1, 0, 0))
for _, n in { "Iris_L", "Iris_R" } do
	local d = actualWorld(world, inst, n)
	check(d:Dot(faceRight) > 0.035, n .. " should move toward the character's right")
end
ctrl:SetLook(nil)

-- blush slides out of the head along the cheek normal
ctrl:SetBlush(true)
step(2)
local bz = actualWorld(world, inst, "Blush_L")
check(math.abs(bz.Magnitude - Presets.BlushShow) < 1e-3, "blush should move out by BlushShow")
ctrl:SetBlush(false)

-- 2D mouth images: helpers
local function mouthInfo(name)
	for _, m in Presets.Mouths do
		if m.Name == name then
			return m
		end
	end
end
local function mouthShown(name)
	local m = mouthInfo(name)
	local want = expectedWorld(m.Bone, Vector3.new(0, 0, m.Show))
	return (actualWorld(world, inst, m.Bone) - want).Magnitude < 1e-4
end
local function shownMouths()
	local out = {}
	for _, m in Presets.Mouths do
		if mouthShown(m.Name) then
			table.insert(out, m.Name)
		end
	end
	return out
end

-- exactly one mouth image is out at a time, and it swaps instantly (no fade)
ctrl:SetBlush(false)
ctrl:SetExpression("Neutral", 0.01)
step(0.3)
check(#shownMouths() == 1 and mouthShown(Presets.DefaultMouth), "Neutral should show only the default mouth")
ctrl:SetExpression("Laugh", 2.0) -- slow fade for the eyes and brows...
step(1 / 60)
check(#shownMouths() == 1 and mouthShown("Laugh"), "...but the mouth image swaps on the next frame")

-- SetMouth overrides the expression's mouth until cleared
ctrl:SetMouth("O")
step(1 / 60)
check(#shownMouths() == 1 and mouthShown("O"), "SetMouth should show the requested image")
ctrl:SetMouth(nil)
step(1 / 60)
check(mouthShown("Laugh"), "SetMouth(nil) should return to the expression's mouth")
check(ctrl:SetMouth("NotAMouth") == false, "unknown mouths should be rejected")

-- talking flips between talk images and the expression's mouth, one image at a time
ctrl:SetExpression("Smile", 0.01)
step(0.3)
ctrl:Talk(1.5)
local seen, single = {}, true
for _ = 1, 90 do
	step(1 / 60)
	local s = shownMouths()
	if #s ~= 1 then
		single = false
	end
	if s[1] then
		seen[s[1]] = true
	end
end
local talkSeen = 0
for _, t in Presets.TalkMouths do
	if seen[t.Name] then
		talkSeen += 1
	end
end
check(single, "exactly one mouth image should be visible while talking")
check(talkSeen >= 2, "talking should flip through several mouth images")
check(seen.Smile == true, "the expression's mouth should show between syllables")
step(1.0)
check(#shownMouths() == 1 and mouthShown("Smile"), "the mouth should return to the expression after talking")

-- disabling hands bones back (identity transforms)
ctrl:SetEnabled(false)
local allZero = true
for _, b in inst do
	if b.Transform.Position.Magnitude > 1e-9 then
		allZero = false
	end
end
check(allZero, "SetEnabled(false) should reset bones")
ctrl:Destroy()

------------------------------------------------------------------ attach()
local character = Instance.new("Model")
character.Name = "Dummy"
local head = Instance.new("Part")
head.Name = "Head"
head.CFrame = CFrame.new(-4, 7.5, 12) * CFrame.Angles(0, 0.7, 0.05)
head.Color = Color3.fromRGB(240, 200, 170)
head.Parent = character
local decal = Instance.new("Decal")
decal.Name = "face"
decal.Parent = head

local tmpl = buildTemplate()
local face = AnimeFace.attach(character, tmpl)
local rigPart = face:FindFirstChild("AnimeFace")
local bones = AnimeFace.collectBones(face)
local frame = AnimeFace._computeFaceFrame(bones)
check((frame.Position - head.CFrame.Position).Magnitude < 1e-5, "face centre should sit on the head centre")
for _, axis in { Vector3.new(1, 0, 0), Vector3.new(0, 1, 0), Vector3.new(0, 0, 1) } do
	local a = rot(frame):VectorToWorldSpace(axis)
	local b = rot(head.CFrame):VectorToWorldSpace(axis)
	check(a:Dot(b) > 0.99999, "face axes should match the head axes")
end
local joint = head:FindFirstChild(AnimeFace.JointName)
check(joint ~= nil and joint.Part1 == rigPart and joint.Part0 == head, "Motor6D should join Head -> face")
if joint then
	local mounted = head.CFrame * joint.C0 * joint.C1:Inverse()
	check((mounted.Position - rigPart.CFrame.Position).Magnitude < 1e-5, "joint offsets should reproduce the placement")
end
check(head.Transparency == 1 and decal.Transparency == 1, "original head and face decal should be hidden")
check(rigPart.Color == head.Color, "face should take the head colour")
check(face:GetAttribute("FaceExpression") == "Neutral", "face should carry the expression attribute")
check(face.Parent == character and rigPart.Massless and not rigPart.CanCollide, "face should be a massless child of the character")

AnimeFace.setExpression(character, "Angry")
check(face:GetAttribute("FaceExpression") == "Angry", "setExpression should set the attribute")
AnimeFace.setExpression(character, "NotAnExpression")
check(face:GetAttribute("FaceExpression") == "Angry", "unknown expressions should be ignored")

print(string.format("%d checks, %d failures", checks, failures))
if failures > 0 then
	error("tests failed")
end

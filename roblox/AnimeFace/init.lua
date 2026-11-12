--[[
	AnimeFace — controller for the AnimeFace R6 skinned face rig.

	Server:
		local face = AnimeFace.attach(character, template)   -- clones + mounts the face on the Head
		AnimeFace.setExpression(character, "Happy")           -- replicated through attributes
		AnimeFace.setMouth(character, "Grin")                 -- force a 2D mouth image (nil = auto)
		AnimeFace.setBlush(character, 1)
		AnimeFace.talk(character, "hello there")

	Client (bone transforms are local, so every client drives the faces it can see):
		local ctrl = AnimeFace.new(face):BindToAttributes()
		ctrl:SetExpression("Smile")  ctrl:SetMouth("O")  ctrl:Blink()  ctrl:SetLook(0.5, 0)
		ctrl:Talk("some text")  ctrl:SetBlush(true)  ctrl:SetEnabled(false)  -- hand control to animations

	The mouth is a set of flat 2D images. Each image sits on its own bone (Mouth_<Name>): the one
	shown rests on the skin and the others are pushed just inside the head, so swapping images is
	instant and works the same from scripts or from Animation Editor keyframes.

	Offsets come from the Presets module (generated from the Blender rig). The controller calibrates
	itself from the bones' rest positions, so it works whatever axis convention the importer used.
]]

local RunService = game:GetService("RunService")

local Presets = require(script:WaitForChild("Presets"))

local AnimeFace = {}
AnimeFace.__index = AnimeFace
AnimeFace.Presets = Presets
AnimeFace.Tag = "AnimeFace"
AnimeFace.FaceName = "AnimeFace"
AnimeFace.JointName = "AnimeFaceJoint"

local ZERO = Vector3.new(0, 0, 0)
local UP = Vector3.new(0, 1, 0)
local REQUIRED = { "FaceRoot", "Eye_L", "Eye_R", "Brow_L", "Brow_R", "Iris_L", "Iris_R" }

-- Static bone info from the generated presets.
local BONE_INFO = {}
local BONE_COUNT = 0
for _, b in Presets.Bones do
	local side = 0
	local suffix = string.sub(b.Name, -2)
	if suffix == "_L" then
		side = -1
	elseif suffix == "_R" then
		side = 1
	end
	BONE_INFO[b.Name] = { Parent = b.Parent, Angle = b.Angle, Side = side }
	BONE_COUNT += 1
end

local function toVectors(offsets)
	local out = {}
	for name, v in offsets do
		out[name] = Vector3.new(v[1], v[2], v[3])
	end
	return out
end

local EXPRESSIONS = {}
for name, e in Presets.Expressions do
	EXPRESSIONS[name] = { Blink = e.Blink, Mouth = e.Mouth or Presets.DefaultMouth, Offsets = toVectors(e.Offsets) }
end

local CLOSED = EXPRESSIONS.Blink.Offsets
local LIDS, UPPER_LIDS, LOWER_LIDS, BLUSH = {}, {}, {}, {}
for _, side in { "L", "R" } do
	for _, base in { "LidUpperInner", "LidUpper", "LidUpperOuter" } do
		LIDS[base .. "_" .. side] = true
		UPPER_LIDS[base .. "_" .. side] = true
	end
	LIDS["LidLower_" .. side] = true
	LOWER_LIDS["LidLower_" .. side] = true
	BLUSH["Blush_" .. side] = true
end

-- 2D mouth images: each sits on its own bone; the shown one is on the skin, the rest inside the head.
local MOUTH_BY_BONE, MOUTH_NAMES = {}, {}
for _, m in Presets.Mouths do
	MOUTH_BY_BONE[m.Bone] = m
	MOUTH_NAMES[m.Name] = true
end
local TALK_TOTAL = 0
for _, t in Presets.TalkMouths do
	TALK_TOTAL += t.Weight
end

---------------------------------------------------------------------------------------------------
-- Rig helpers
---------------------------------------------------------------------------------------------------
local function rotationOnly(cf)
	return cf - cf.Position
end

-- Rest (un-animated) world CFrame of a bone, walking up through parent bones to the owning part.
local function restWorldCFrame(inst)
	local parent = inst.Parent
	if parent and parent:IsA("Bone") then
		return restWorldCFrame(parent) * inst.CFrame
	elseif parent and parent:IsA("BasePart") then
		return parent.CFrame * inst.CFrame
	end
	return inst.CFrame
end

local function owningPart(inst)
	local p = inst.Parent
	while p and not p:IsA("BasePart") do
		p = p.Parent
	end
	return p
end

function AnimeFace.collectBones(root)
	local bones, count = {}, 0
	for _, d in root:GetDescendants() do
		if d:IsA("Bone") and BONE_INFO[d.Name] and not bones[d.Name] then
			bones[d.Name] = d
			count += 1
		end
	end
	return bones, count
end

-- Orthonormal basis from the eyes (X) and brows (Y); the same construction on the design positions
-- and on the imported rest positions gives the exact rotation between them.
local function eyeBrowBasis(eL, eR, bL, bR)
	local e1 = (eR - eL).Unit
	local v2 = (bL + bR) / 2 - (eL + eR) / 2
	local e2 = (v2 - e1 * e1:Dot(v2)).Unit
	return CFrame.fromMatrix(ZERO, e1, e2, e1:Cross(e2))
end

local DESIGN = {}
for _, b in Presets.Bones do
	DESIGN[b.Name] = Vector3.new(b.Position[1], b.Position[2], b.Position[3])
end
local DESIGN_BASIS = eyeBrowBasis(DESIGN.Eye_L, DESIGN.Eye_R, DESIGN.Brow_L, DESIGN.Brow_R)

-- Face frame in world space at rest: X = character right, Y = up, Z = back (face looks along -Z).
local function computeFaceFrame(bones)
	local pL = restWorldCFrame(bones.Eye_L).Position
	local pR = restWorldCFrame(bones.Eye_R).Position
	local bL = restWorldCFrame(bones.Brow_L).Position
	local bR = restWorldCFrame(bones.Brow_R).Position
	local centre = restWorldCFrame(bones.FaceRoot).Position
	local headToWorld = eyeBrowBasis(pL, pR, bL, bR) * DESIGN_BASIS:Inverse()
	local frame = CFrame.new(centre) * headToWorld
	local back = headToWorld:VectorToWorldSpace(Vector3.new(0, 0, 1))
	local frontOk = ((pL + pR) / 2 - centre):Dot(back) < 0
	return frame, (pR - pL).Magnitude, frontOk
end
AnimeFace._computeFaceFrame = computeFaceFrame
AnimeFace._restWorldCFrame = restWorldCFrame

-- Waits (client side) until every face bone has replicated. Returns true when ready.
function AnimeFace.waitForRig(face, timeout)
	local deadline = os.clock() + (timeout or 10)
	repeat
		local _, count = AnimeFace.collectBones(face)
		if count >= BONE_COUNT then
			return true
		end
		task.wait(0.1)
	until os.clock() > deadline or not face.Parent
	return false
end

---------------------------------------------------------------------------------------------------
-- Mounting (server or client)
---------------------------------------------------------------------------------------------------
local function forEachPart(root, fn)
	if root:IsA("BasePart") then
		fn(root)
	end
	for _, d in root:GetDescendants() do
		if d:IsA("BasePart") then
			fn(d)
		end
	end
end

--[[
	Clones `template` (the imported face Model or MeshPart) onto character.Head.
	options:
		SkinColor: Color3?   fixed skin tone (default: follow the Head's Color)
		HideHead: boolean?   hide the original head mesh and face decal (default true)
		Scale: number?       uniform scale for non-default head sizes (Model templates only)
		Expression: string?  initial expression (default "Neutral")
]]
function AnimeFace.attach(character, template, options)
	options = options or {}
	local head = character:FindFirstChild("Head")
	assert(head and head:IsA("BasePart"), "AnimeFace.attach: character has no Head part")
	local previous = character:FindFirstChild(AnimeFace.FaceName)
	if previous then
		previous:Destroy()
	end
	local oldJoint = head:FindFirstChild(AnimeFace.JointName)
	if oldJoint then
		oldJoint:Destroy()
	end

	local face = template:Clone()
	face.Name = AnimeFace.FaceName
	if options.Scale and face:IsA("Model") then
		face:ScaleTo(options.Scale)
	end
	local bones = AnimeFace.collectBones(face)
	for _, name in REQUIRED do
		assert(bones[name], "AnimeFace.attach: template is missing bone " .. name)
	end
	local rigPart = owningPart(bones.FaceRoot)
	assert(rigPart, "AnimeFace.attach: bones are not inside a BasePart")

	local frame, _, frontOk = computeFaceFrame(bones)
	if not frontOk then
		warn("AnimeFace: the imported rig looks mirrored; check the FBX export axes")
	end
	local frameRel = rigPart.CFrame:ToObjectSpace(frame)

	-- keep any extra parts from the import where they were relative to the rig part
	local others = {}
	forEachPart(face, function(p)
		p.Anchored = false
		p.CanCollide = false
		p.CanQuery = false
		p.CanTouch = false
		p.Massless = true
		p.CastShadow = options.CastShadow == true
		if p ~= rigPart then
			others[p] = rigPart.CFrame:ToObjectSpace(p.CFrame)
		end
	end)
	rigPart.CFrame = head.CFrame * frameRel:Inverse()
	for p, rel in others do
		p.CFrame = rigPart.CFrame * rel
		local weld = Instance.new("WeldConstraint")
		weld.Part0 = rigPart
		weld.Part1 = p
		weld.Parent = p
	end

	local joint = Instance.new("Motor6D")
	joint.Name = AnimeFace.JointName
	joint.Part0 = head
	joint.Part1 = rigPart
	joint.C0 = CFrame.new()
	joint.C1 = frameRel
	joint.Parent = head

	local function paint()
		local skin = options.SkinColor or head.Color
		forEachPart(face, function(p)
			if p:IsA("MeshPart") then
				p.Color = skin
			end
		end)
	end
	paint()

	local function hideDecal(d)
		if d:IsA("Decal") then
			d.Transparency = 1
		end
	end
	if options.HideHead ~= false then
		head.Transparency = 1
		for _, d in head:GetChildren() do
			hideDecal(d)
		end
	end

	face:SetAttribute("FaceExpression", options.Expression or "Neutral")
	face:SetAttribute("FaceBlush", 0)
	face.Parent = character
	face:AddTag(AnimeFace.Tag)

	-- avatar appearance can load after the face is mounted: keep colour and decals in sync
	-- (pcall: signals are unavailable in offline test runtimes)
	pcall(function()
		local conns = {}
		if not options.SkinColor then
			table.insert(conns, head:GetPropertyChangedSignal("Color"):Connect(paint))
		end
		if options.HideHead ~= false then
			table.insert(conns, head.ChildAdded:Connect(hideDecal))
		end
		face.Destroying:Connect(function()
			for _, c in conns do
				c:Disconnect()
			end
		end)
	end)
	return face
end

local function faceOf(target)
	if target:GetAttribute("FaceExpression") ~= nil then
		return target
	end
	return target:FindFirstChild(AnimeFace.FaceName)
end

-- Server-side helpers: they set attributes on the face, which every client controller follows.
function AnimeFace.setExpression(target, name)
	local face = faceOf(target)
	if face and EXPRESSIONS[name] then
		face:SetAttribute("FaceExpression", name)
	end
end

function AnimeFace.setBlush(target, amount)
	local face = faceOf(target)
	if face then
		face:SetAttribute("FaceBlush", math.clamp(tonumber(amount) or 0, 0, 1))
	end
end

function AnimeFace.setLook(target, x, y)
	local face = faceOf(target)
	if face then
		face:SetAttribute("FaceLook", if x then Vector2.new(x, y or 0) else nil)
	end
end

-- true: stop the procedural controller so Animation Editor animations drive the face bones
function AnimeFace.setManual(target, manual)
	local face = faceOf(target)
	if face then
		face:SetAttribute("FaceManual", manual == true)
	end
end

-- Force one 2D mouth image (nil = follow the expression).
function AnimeFace.setMouth(target, name)
	local face = faceOf(target)
	if face and (name == nil or MOUTH_NAMES[name]) then
		face:SetAttribute("FaceMouth", name)
	end
end

local talkSerial = 0
function AnimeFace.talk(target, text)
	local face = faceOf(target)
	if face then
		talkSerial += 1
		face:SetAttribute("FaceTalk", tostring(talkSerial) .. "|" .. tostring(text))
	end
end

---------------------------------------------------------------------------------------------------
-- Controller
---------------------------------------------------------------------------------------------------
local active = {}
local loop = nil

local function ensureLoop()
	if loop then
		return
	end
	loop = RunService.PreSimulation:Connect(function(dt)
		for ctrl in active do
			local ok, err = pcall(ctrl._step, ctrl, dt)
			if not ok then
				warn("AnimeFace controller stopped: " .. tostring(err))
				active[ctrl] = nil
			end
		end
	end)
end

local function randomRange(a, b)
	return a + (b - a) * math.random()
end

--[[
	options:
		AutoBlink: boolean? (default true)    AutoLook: boolean? idle eye movement (default true)
		CullDistance: number? skip updates when the camera is farther than this (default 150)
]]
function AnimeFace.new(face, options)
	options = options or {}
	local self = setmetatable({}, AnimeFace)
	self.Face = face
	local bones = AnimeFace.collectBones(face)
	for _, name in REQUIRED do
		assert(bones[name], "AnimeFace.new: face is missing bone " .. name)
	end
	self.Bones = bones
	self.RigPart = owningPart(bones.FaceRoot)

	local frame, eyeDistance, frontOk = computeFaceFrame(bones)
	if not frontOk then
		warn("AnimeFace: the imported rig looks mirrored; check the FBX export axes")
	end
	self.Scale = eyeDistance / Presets.DesignEyeDistance
	self._frameRel = self.RigPart.CFrame:ToObjectSpace(frame)
	local frameRot = rotationOnly(frame)
	self._map = {}
	for name, bone in bones do
		local info = BONE_INFO[name]
		local a = info.Angle
		self._map[name] = {
			Bone = bone,
			-- maps face-frame vectors into the bone's local space (Bone.Transform is bone-local)
			Conv = rotationOnly(restWorldCFrame(bone)):Inverse() * frameRot,
			T = Vector3.new(math.cos(a), 0, math.sin(a)),
			N = Vector3.new(math.sin(a), 0, -math.cos(a)),
			Side = if info.Side ~= 0 then info.Side else 1,
			Last = nil,
		}
	end

	self.Enabled = true
	self.Expression = "Neutral"
	self.AutoBlink = options.AutoBlink ~= false
	self.AutoLook = options.AutoLook ~= false
	self.CullDistance = options.CullDistance or 150
	self._exprTarget = {}
	self._exprCur = {}
	self._exprSpeed = 25
	self._blinkAllowed = true
	self._nextBlink = os.clock() + randomRange(1.2, 3.5)
	self._blinkStart = nil
	self._eyesClosed = 0
	self._lookOverride = nil
	self._lookAtPos = nil
	self._lookCur = Vector2.new(0, 0)
	self._saccade = Vector2.new(0, 0)
	self._nextSaccade = os.clock() + randomRange(1, 3)
	self._blushTarget = 0
	self._blushCur = 0
	self._talkUntil = 0
	self._syllable = nil
	self._lastSyllableOpen = false
	self._mouthOverride = nil
	self.Mouth = Presets.DefaultMouth
	self._conns = {}
	active[self] = true
	ensureLoop()
	return self
end

function AnimeFace:SetExpression(name, fadeTime)
	local e = EXPRESSIONS[name]
	if not e then
		warn("AnimeFace: unknown expression " .. tostring(name))
		return false
	end
	self.Expression = name
	self._exprTarget = e.Offsets
	self._blinkAllowed = e.Blink
	self._exprSpeed = 4.6 / math.max(fadeTime or 0.18, 0.01)
	return true
end

function AnimeFace:GetExpressions()
	return table.clone(Presets.ExpressionOrder)
end

-- Show one 2D mouth image regardless of the expression (nil = back to the expression's mouth).
function AnimeFace:SetMouth(name)
	if name ~= nil and not MOUTH_NAMES[name] then
		warn("AnimeFace: unknown mouth " .. tostring(name))
		return false
	end
	self._mouthOverride = name
	return true
end

function AnimeFace:GetMouths()
	local out = {}
	for _, m in Presets.Mouths do
		table.insert(out, m.Name)
	end
	return out
end

function AnimeFace:Blink()
	if self._blinkStart == nil then
		self._blinkStart = os.clock()
	end
end

-- Manually close the eyes (0..1), e.g. for sleeping. Blinks still play on top.
function AnimeFace:SetEyesClosed(amount)
	self._eyesClosed = math.clamp(amount or 0, 0, 1)
end

-- x, y in -1..1 (x > 0 = toward the character's right, y > 0 = up). Pass nil to release.
function AnimeFace:SetLook(x, y)
	if x == nil then
		self._lookOverride = nil
	else
		local v = Vector2.new(x, y or 0)
		if v.Magnitude > 1 then
			v = v.Unit
		end
		self._lookOverride = v
	end
end

function AnimeFace:LookAt(position)
	self._lookAtPos = position
end

function AnimeFace:SetBlush(amount)
	if amount == true then
		amount = 1
	elseif amount == false or amount == nil then
		amount = 0
	end
	self._blushTarget = math.clamp(amount, 0, 1)
end

-- Talk for a duration (seconds) or for roughly as long as it takes to say `text`.
function AnimeFace:Talk(textOrSeconds)
	local duration
	if type(textOrSeconds) == "number" then
		duration = textOrSeconds
	else
		duration = math.clamp(#tostring(textOrSeconds or "") * 0.055, 0.4, 8)
	end
	self._talkUntil = math.max(self._talkUntil, os.clock() + duration)
end

function AnimeFace:StopTalking()
	self._talkUntil = 0
end

function AnimeFace:SetEnabled(enabled)
	self.Enabled = enabled
	if not enabled then
		self:_resetBones()
	end
end

function AnimeFace:_resetBones()
	for _, m in self._map do
		if m.Bone.Parent then
			m.Bone.Transform = CFrame.new()
		end
		m.Last = nil
	end
end

function AnimeFace:BindToAttributes()
	local face = self.Face
	local function apply()
		local expr = face:GetAttribute("FaceExpression")
		if type(expr) == "string" and expr ~= self.Expression then
			self:SetExpression(expr)
		end
		local blush = face:GetAttribute("FaceBlush")
		if type(blush) == "number" then
			self:SetBlush(blush)
		end
		local look = face:GetAttribute("FaceLook")
		if typeof(look) == "Vector2" then
			self:SetLook(look.X, look.Y)
		else
			self:SetLook(nil)
		end
		local mouth = face:GetAttribute("FaceMouth")
		self:SetMouth(if type(mouth) == "string" and MOUTH_NAMES[mouth] then mouth else nil)
		-- FaceManual = true hands the bones to hand-made animations (Animation Editor tracks)
		local manual = face:GetAttribute("FaceManual") == true
		if manual == self.Enabled then
			self:SetEnabled(not manual)
		end
	end
	table.insert(self._conns, face.AttributeChanged:Connect(function(attr)
		if attr == "FaceTalk" then
			local value = face:GetAttribute("FaceTalk")
			if type(value) == "string" then
				local text = string.match(value, "^%d+|(.*)$") or value
				self:Talk(text)
			end
		else
			apply()
		end
	end))
	apply()
	return self
end

function AnimeFace:Destroy()
	active[self] = nil
	for _, c in self._conns do
		c:Disconnect()
	end
	table.clear(self._conns)
	self:_resetBones()
end

---------------------------------------------------------------------------------------------------
-- Per-frame update
---------------------------------------------------------------------------------------------------
function AnimeFace:_blinkAmount(now)
	if self._blinkStart == nil and self.AutoBlink and now >= self._nextBlink then
		self._blinkStart = now
	end
	local b = 0
	if self._blinkStart then
		local t = now - self._blinkStart
		local CLOSE, HOLD, OPEN = 0.07, 0.04, 0.13
		if t < CLOSE then
			local u = t / CLOSE
			b = u * u
		elseif t < CLOSE + HOLD then
			b = 1
		elseif t < CLOSE + HOLD + OPEN then
			local u = (t - CLOSE - HOLD) / OPEN
			b = 1 - u * u * (3 - 2 * u)
		else
			self._blinkStart = nil
			-- occasional double blink
			self._nextBlink = now + (if math.random() < 0.15 then 0.18 else randomRange(2.0, 5.5))
		end
	end
	if not self._blinkAllowed then
		b = 0
	end
	return math.max(b, self._eyesClosed)
end

function AnimeFace:_lookTarget(now)
	if self._lookOverride then
		return self._lookOverride
	end
	if self._lookAtPos and self.RigPart then
		local frame = self.RigPart.CFrame * self._frameRel
		local rel = frame:PointToObjectSpace(self._lookAtPos)
		if rel.Z < -0.2 then
			local yaw = math.atan2(rel.X, -rel.Z)
			local pitch = math.atan2(rel.Y, math.sqrt(rel.X * rel.X + rel.Z * rel.Z))
			return Vector2.new(math.clamp(yaw / math.rad(40), -1, 1), math.clamp(pitch / math.rad(30), -1, 1))
		end
	end
	if self.AutoLook then
		if now >= self._nextSaccade then
			self._nextSaccade = now + randomRange(1.2, 3.8)
			if math.random() < 0.45 then
				self._saccade = Vector2.new(0, 0)
			else
				self._saccade = Vector2.new(randomRange(-0.3, 0.3), randomRange(-0.18, 0.12))
			end
		end
		return self._saccade
	end
	return Vector2.new(0, 0)
end

-- Talking flips through 2D mouth images, with the expression's own mouth between syllables.
function AnimeFace:_talkMouth(now)
	local syl = self._syllable
	if syl and now >= syl.Start + syl.Duration then
		syl = nil
		self._syllable = nil
	end
	if not syl and now < self._talkUntil then
		local closed = self._lastSyllableOpen and math.random() < 0.55
		local pick = nil
		if not closed then
			local roll = math.random() * TALK_TOTAL
			for _, t in Presets.TalkMouths do
				roll -= t.Weight
				pick = t.Name
				if roll <= 0 then
					break
				end
			end
		end
		syl = {
			Mouth = pick, -- nil = closed (the expression's mouth)
			Start = now,
			Duration = if closed then randomRange(0.05, 0.09) else randomRange(0.08, 0.15),
		}
		self._lastSyllableOpen = pick ~= nil
		self._syllable = syl
	end
	return syl and syl.Mouth
end

function AnimeFace:_currentMouth(now)
	return self:_talkMouth(now) or self._mouthOverride or EXPRESSIONS[self.Expression].Mouth
end

function AnimeFace:_write(m, off)
	local last = m.Last
	if last and (last - off).Magnitude < 1e-6 then
		return
	end
	m.Last = off
	local d = (m.T * (off.X * m.Side) + UP * off.Y + m.N * off.Z) * self.Scale
	m.Bone.Transform = CFrame.new(m.Conv:VectorToWorldSpace(d))
end

function AnimeFace:_step(dt)
	if not self.Enabled then
		return
	end
	local now = os.clock()

	-- expression easing (mouth images swap instantly instead, see below)
	local k = 1 - math.exp(-self._exprSpeed * dt)
	for name in self._map do
		if MOUTH_BY_BONE[name] then
			continue
		end
		local target = self._exprTarget[name] or ZERO
		local cur = self._exprCur[name] or ZERO
		if cur ~= target then
			local nxt = cur:Lerp(target, k)
			if (nxt - target).Magnitude < 1e-5 then
				nxt = target
			end
			self._exprCur[name] = nxt
		end
	end

	local blink = self:_blinkAmount(now)
	local lt = self:_lookTarget(now)
	self._lookCur = self._lookCur:Lerp(lt, 1 - math.exp(-22 * dt))
	self._blushCur += (self._blushTarget - self._blushCur) * (1 - math.exp(-6 * dt))
	local shownMouth = self:_currentMouth(now)
	self.Mouth = shownMouth

	if self.CullDistance and workspace.CurrentCamera and self.RigPart then
		local dist = (workspace.CurrentCamera.CFrame.Position - self.RigPart.Position).Magnitude
		if dist > self.CullDistance then
			return
		end
	end

	local look = self._lookCur
	local range = Presets.LookRange
	local blushZ = Presets.BlushShow * self._blushCur
	for name, m in self._map do
		local off = self._exprCur[name] or ZERO
		if LIDS[name] then
			if blink > 0 then
				off = off:Lerp(CLOSED[name] or ZERO, blink)
			end
			if UPPER_LIDS[name] then
				off += Vector3.new(0, look.Y * range.Y * 0.3, 0)
			elseif LOWER_LIDS[name] then
				off += Vector3.new(0, look.Y * range.Y * 0.15, 0)
			end
		end
		if name == "Iris_R" then
			off += Vector3.new(look.X * range.X, look.Y * range.Y, 0)
		elseif name == "Iris_L" then
			off += Vector3.new(-look.X * range.X, look.Y * range.Y, 0)
		end
		local mouth = MOUTH_BY_BONE[name]
		if mouth then
			off = Vector3.new(0, 0, if mouth.Name == shownMouth then mouth.Show else mouth.Hide)
		end
		if BLUSH[name] and blushZ > off.Z then
			off = Vector3.new(off.X, off.Y, blushZ)
		end
		self:_write(m, off)
	end
end

return AnimeFace

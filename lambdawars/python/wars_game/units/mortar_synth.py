from srcbase import *
from vmath import *
from entities import networked, entity, Activity, FireBulletsInfo_t, CreateEntityByName
from fields import BooleanField, UpgradeField
from gameinterface import CPASAttenuationFilter, CPVSFilter, CPASFilter
from core.units import (UnitInfo, UnitBaseCombat as BaseClass, UnitBaseAirLocomotion, CreateUnitNoSpawn,
    EventHandlerAnimation, GetUnitInfo, UnitBaseAnimState, UnitCombatLocomotion)

if isserver:
    from core.units import UnitCombatAirNavigator, BaseAction, UnitCombatNavigator
    from utils import ExplosionCreate
    from sound import ATTN_NONE
    from gameinterface import CPASAttenuationFilter
    from entities import CEntityFlame, SmokeTrail
import random

@entity('unit_mortar_synth', networked=True)
class UnitMortarSynth(BaseClass):
    aiclimb = False
    LocomotionClass = UnitBaseAirLocomotion
    acttables = {
        Activity.ACT_IDLE : Activity.ACT_IDLE,
    }
    gibmodelnames = [
        'models\Gibs\mortarsynth_gib_1.mdl',
        'models\Gibs\mortarsynth_gib_2.mdl',
        'models\Gibs\mortarsynth_gib_3.mdl',
        'models\Gibs\mortarsynth_gib_4.mdl',
        'models\Gibs\mortarsynth_gib_5.mdl',
    ]
    def Precache(self):
        super().Precache()
        for gibmodelname in self.gibmodelnames:
            self.PrecacheModel(gibmodelname)
        if isserver:
            self.PrecacheScriptSound('Weapon_Mortar.Single')
    if isserver:
        NavigatorClass = UnitCombatAirNavigator
        
        __firetimeout = 0.25
        
        def StartRangeAttack(self, enemy):
            if (gpGlobals.curtime - self.nextattacktime) > self.__firetimeout:
                self.nextattacktime = gpGlobals.curtime - 0.001
        
            info = self.abilitiesbyname.get('mortarattack', None)
            
            while self.nextattacktime < gpGlobals.curtime and self.abilitycheckautocast.get(info.uid, False):
                attackinfo = self.unitinfo.AttackRange
                self.nextattacktime += attackinfo.attackspeed
                self.DoAnimation(self.ANIM_RANGE_ATTACK1)
                #self.ThrowEnergyGrenade()
            return False
    else:
        def StartRangeAttack(self, enemy):
            self.DoAnimation(self.ANIM_RANGE_ATTACK1)
            return False
    
    def __init__(self):
        super().__init__()
        self.savedrop = 2048.0
        self.maxclimbheight = 192.0
        self.testroutestartheight = 2048.0
        
    def Spawn(self):    
        super().Spawn()
        
        self.SetBloodColor(DONT_BLEED)
        self.locomotion.maxheight = 192.0
        self.locomotion.desiredheight = 192.0
        self.locomotion.flynoiserate = 32.0
        self.locomotion.flynoisez = 24.0
    events = dict(BaseClass.events)
    events.update( {
        'ANIM_RANGE_ATTACK1' : EventHandlerAnimation(Activity.ACT_RANGE_ATTACK1),
    } )
    def MortarSynthAttack(self, event):
        enemy = self.enemy
        if enemy:
            self.ThrowEnergyGrenade(enemy.GetAbsOrigin())
    nextshoottime = 0
    def ThrowEnergyGrenade(self, origin):
        unit = self
        enemy = unit.enemy
        grenades = self.unitinfo.grenades
        if origin and not self.nextshoottime > gpGlobals.curtime:
            info = unit.unitinfo.AttackRange
            vGrenadePos = self.GetAbsOrigin() + Vector(0,0,20)

            #vTarget = Vector()
            #UTIL_PredictedPosition( enemy, 0.5, vTarget ) 
            #vTarget = enemy.GetAbsOrigin()
            vTarget = origin

            from unit_helper import TossGrenadeAnimEventHandler #TODO: FIX THIS
            handler = TossGrenadeAnimEventHandler("grenade_energy", 650)
            
            for i in range(0, grenades):
                if grenades > 1:
                    position = Vector(random.randint(-90,90),random.randint(-90,90), 0)
                else:
                    position = Vector(0,0,0)
                grenade = handler.TossGrenade(unit, vGrenadePos, vTarget + position, unit.CalculateIgnoreOwnerCollisionGroup())
                if grenade:
                    grenade.damage = info.damage
                    grenade.damagetype = DMG_BLAST
                    grenade.damageradius = info.radiusdamage
                    grenade.SetThrower(self)
                
                    filter = CPASAttenuationFilter(self, ATTN_NONE)

                    self.EmitSoundFilter( filter, self.entindex(), "Weapon_Mortar.Single" )
                    #info = self.abilitiesbyname.get('mortarattack', None)
                    #info.SetRecharge(info.unit)
                    self.nextshoottime = gpGlobals.curtime + self.unitinfo.AttackRange.attackspeed
    def PreDetonate(self):
        #self.Hop(10) #не вижу смысла
        self.SetTouch(None)
        self.SetThink(self.Explode)
        self.SetNextThink(gpGlobals.curtime + 0.1)
        #self.SetNextThink(gpGlobals.curtime + 1.0)

        #self.EmitSound("") #если нужен какой-то особый звук
    def Explode(self):
        self.takedamage = DAMAGE_NO
        ExplosionCreate(self.WorldSpaceCenter(), self.GetLocalAngles(), self, 1, 150, True ) #где 1 - это урон. 150 это радиус

        info = CTakeDamageInfo(self, self, 1, DMG_GENERIC)
        self.Event_Killed(info)

        # Remove myself a frame from now to avoid doing it in the middle of running AI
        self.SetThink(self.SUB_Remove)
        self.SetNextThink(gpGlobals.curtime)
        nGib = 5 #где 5 - это скока гибов будет в итоге.  можешь сделать в виде рандома как ниже
        #nGib = random.randint(2,5)
        for i in range(1, nGib): 
            self.ThrowGibs(i)
    def ThrowGibs(self, i):
        ''' Character killed (only fired once) '''
        vecAbsMins = Vector();
        vecAbsMaxs = Vector()
        self.CollisionProp().WorldSpaceAABB(vecAbsMins, vecAbsMaxs)

        vecNormalizedMins = Vector();
        vecNormalizedMaxs = Vector()
        self.CollisionProp().WorldToNormalizedSpace(vecAbsMins, vecNormalizedMins)
        self.CollisionProp().WorldToNormalizedSpace(vecAbsMaxs, vecNormalizedMaxs)

        vecAbsPoint = Vector()
        filter = CPASFilter(self.GetAbsOrigin())
        self.CollisionProp().RandomPointInBounds(vecNormalizedMins, vecNormalizedMaxs, vecAbsPoint)

        # Throw a flaming, smoking chunk.
        pChunk = CreateEntityByName("gib")
        pChunk.Spawn("models/gibs/hgibs.mdl")
        pChunk.SetBloodColor(DONT_BLEED)

        vecSpawnAngles = QAngle()
        vecSpawnAngles.Random(-90, 90)
        pChunk.SetAbsOrigin(vecAbsPoint)
        pChunk.SetAbsAngles(vecSpawnAngles)

        pChunk.Spawn(self.gibmodelnames[i])
        pChunk.SetOwnerEntity(self)
        pChunk.lifetime = random.uniform(6.0, 8.0) #время жизни если что
        pChunk.SetCollisionGroup(COLLISION_GROUP_DEBRIS)
        pPhysicsObject = pChunk.VPhysicsInitNormal(SOLID_VPHYSICS, pChunk.GetSolidFlags(), False)

        # Set the velocity
        if pPhysicsObject:
            pPhysicsObject.EnableMotion(True)
            vecVelocity = Vector()

            angles = QAngle()
            angles.x = random.uniform(-20, 20)
            angles.y = random.uniform(0, 360)
            angles.z = 0.0
            AngleVectors(angles, vecVelocity)

            vecVelocity *= random.uniform(300, 900) #можешь настроить скорость и импульс чтобы части не улетали за 100 км или наоборот
            vecVelocity += self.GetAbsVelocity()

            angImpulse = AngularImpulse()
            angImpulse = RandomAngularImpulse(-180, 180)

            pChunk.SetAbsVelocity(vecVelocity)
            pPhysicsObject.SetVelocity(vecVelocity, angImpulse)
        #будут ли гибы гореть
        pFlame = CEntityFlame.Create(pChunk, False)
        if pFlame != None:
            pFlame.SetLifetime(pChunk.lifetime)
    if isserver:
        class BehaviorGenericClass(BaseClass.BehaviorGenericClass):
            class ActionDie(BaseAction):
                def OnStart(self):
                    # Will remove the unit after explode:
                    self.outer.PreDetonate()

        aetable = {
            1 : MortarSynthAttack,
        }
class MortarSynthInfo(UnitInfo):
    name = 'unit_mortar_synth'
    cls_name = 'unit_mortar_synth'
    displayname = '#CombMortarSynth_Name'
    description = '#CombMortarSynth_Description'
    image_name = 'vgui/combine/units/unit_mortar_synth'
    modelname = 'models/MortarSynth.mdl'
    health = 150
    buildtime = 28.0
    costs = [('requisition', 45), ('power', 25)]
    attributes = ['synth']
    maxspeed = 112
    turnspeed = 200
    viewdistance = 768
    sensedistance = 1408
    techrequirements = ['build_comb_tech_center']
    population = 2
    scalebounds = 0.80
    grenades = 1
    abilities = {
        0 : 'mortarattack',
        8: 'attackmove',
        9: 'holdposition',
        10: 'patrol',
    }
    class AttackRange(UnitInfo.AttackRange):
        cone = 0.7
        damage = 250.0
        attackspeed = 7.0
        maxrange = 1408.0
        radiusdamage = 64
    attacks = ['AttackRange']
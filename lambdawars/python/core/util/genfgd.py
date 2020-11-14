from entities import GetAllClassnames, GetClassByClassname
from gameinterface import concommand
from utils import UTIL_IsCommandIssuedByServerAdmin
from fields import GetAllFields
import operator

basefilecontents = '''//=============================================================================
//
// Purpose: Lambda Wars game definition file (.fgd).
//
// AUTOGENERATED! (Use "generate_fgd")
//
//=============================================================================

@include "base.fgd"
@include "deferred.fgd"

@BaseClass = Wars
[ 
	ownernumber(choices) : "Owner Number" : 0 : "Ownernumber of this entity." =
	[
		0 : "Neutral"
		1 : "Enemy"
		2 : "Player 0"
		3 : "Player 1"
		4 : "Player 2"
		5 : "Player 3"
		6 : "Player 4"
		7 : "Player 5"
		8 : "Player 6"
		9 : "Player 7"
		10 : "Player 8"
		11 : "Player 9"
		12 : "Player 10"
		13 : "Player 11"
	]
	
	input ChangeOwner(integer) : "Change owner of this entity. 0 = Neutral, 1 = Enemy, 2 and further corresponds to Player_1, Player_2, etc."
]

@BaseClass base(Studiomodel, Targetname, Angles, RenderFields, DamageFilter, ResponseContext, Shadow, Wars) color(0 200 200) = BaseUnit
[
    health(integer) : "Health" : 0 : "Unit health (leave 0 for unit type default)"
]

@PointClass base(Angles) = env_detail_controller : "An entity that lets you control the fade distances for detail props."
[
	fademindist(float) : "Start Fade Dist/Pixels" : 400 : "Distance at which the prop starts to fade."
	fademaxdist(float) : "End Fade Dist/Pixels" : 1200 : "Maximum distance at which the prop is visible."
]

@PointClass base(Parentname, Global, Angles, Studiomodel, BreakableProp, DXLevelChoice, BaseFadeProp, RenderFields,Wars) sphere(fademindist) sphere(fademaxdist) studioprop() = wars_flora :
	"" 
[
]

@SolidClass base(Targetname,Parentname,Origin,RenderFields,Global,Inputfilter,EnableDisable,Shadow,Wars)   = fow_blocker :
	"" 
[
]

@PointClass base(Targetname) iconsprite("editor/recast_offmesh_connection.vmt") = recast_offmesh_connection : 
	"Recast off mesh connection. Can be used to add connections manually. For example, to indicate an unit can jump down an edge."
[
    target(target_destination) : "End point" : : "Target entity end point of this entity."
	spawnflags(Flags) = 
	[
		// Type of connection
		1 : "Human" : 1
		2 : "Medium" : 1
		4 : "Large" : 1
		8 : "Very Large" : 1
		16 : "Air" : 0
		
		32 : "Jump down Edge" : 0
	]
]

@PointClass base(Targetname) iconsprite("editor/info_target.vmt") = recast_mgr : 
	"Contains recast navigation mesh settings. Currently only allows disabling certain meshes on maps."
[
	spawnflags(Flags) = 
	[
		// Mesh
		1 : "Disable Mesh Human" : 0
		2 : "Disable Mesh Medium" : 0
		4 : "Disable Mesh Large" : 0
		8 : "Disable Mesh Very Large" : 0
		16 : "Disable Mesh Air" : 0
	]
]

'''

derivedfilecontents = '''//=============================================================================
//
// Purpose: Lambda Wars game definition file (.fgd) 
//
//=============================================================================

@include "lambdawars.fgd"

'''

fgdtemplate = '''%(ClassType)s %(EntityProperties)s %(EntityExtraProperties)s = %(EntityName)s :
	"%(HelpString)s" 
[%(CPPProperties)s
%(PythonProperties)s]
'''

def AddInputMethods(cls, pythonproperties, processed=None):
    # Scan all attributes
    if not processed: 
        processed = set()
    entries = []
    for name, attribute in cls.__dict__.items():
        try:
            entry = attribute.fgdinputentry
            if attribute.inputname in processed:
                continue
        except AttributeError:
            continue
        entries.append( (attribute.inputname, entry) )
        
    for inputname, entry in sorted(entries, key=operator.itemgetter(0)):
        pythonproperties += '\t%s\n'% (entry)
        processed.add(inputname)

    # Now do bases
    for base in cls.__bases__:
        pythonproperties = AddInputMethods(base, pythonproperties, processed)
    return pythonproperties

@concommand('generate_fgd')
def CCGenFGD(args):
    if not UTIL_IsCommandIssuedByServerAdmin():
        return
    gamepackages = set(args.ArgS().split())
    entities = GetAllClassnames()
    entities.sort()

    if gamepackages:
        fgdfilename = '_'.join(gamepackages) + '.fgd'
        content = derivedfilecontents
    else:
        fgdfilename = 'lambdawars.fgd'
        content = basefilecontents
    
    for clsname in entities:
        cls = GetClassByClassname(clsname)
        if not cls:
            continue
            
        if gamepackages:
            try:
                modname = cls.__module__.split('.')[0]
            except: 
                modname = ''
                
            if modname not in gamepackages:
                PrintWarning('Entity class %s is not part of a game package!\n' % (clsname))
                continue

        try:
            factoryname = 'factory__%s' % (clsname)
            factory = getattr(cls, factoryname)
        except AttributeError:
            PrintWarning('generate_fgd: %s has no factory!\n' % (clsname))
            continue
            
        if factory.nofgdentry:
            print('Skipped classname %s. Marked as no fgd entry.' % (clsname))
            continue
            
        # Fields/properties
        pythonproperties = ''
        fields = sorted(GetAllFields(cls), key=operator.attrgetter('name'))
        for field in fields:
            if not field.keyname or field.nofgd:
                continue
                
            pythonproperties += '\t%s\n'% (field.GenerateFGDProperty())
            
        # Inputs. Must check each method
        pythonproperties = AddInputMethods(cls, pythonproperties)
            
        # Entity properties
        entityproperties = ''
        if factory.fgdbase:
            entityproperties += 'base(%s) ' % (','.join(factory.fgdbase))
        if factory.fgdstudio:
            entityproperties += 'studio(%s) ' % ('"%s"' % factory.fgdstudio if factory.fgdstudio != 'null' else '')
        if factory.fgdiconsprite:
            entityproperties += 'iconsprite("%s") ' % (factory.fgdiconsprite)
        if factory.fgdcylinder:
            entityproperties += 'cylinder(%s) ' % (','.join(factory.fgdcylinder))
        if factory.fgdcolor:
            entityproperties += 'color(%s) ' % (factory.fgdcolor)
        if factory.fgdsize:
            entityproperties += 'size(%s) ' % (factory.fgdsize)
            
        content += fgdtemplate % {
            'EntityName': factory.entityname,
            'ClassType': factory.clstype,
            'EntityProperties': entityproperties,
            'EntityExtraProperties': factory.entityextraproperties,
            'HelpString': factory.helpstring,
            'CPPProperties': factory.cppproperties,
            'PythonProperties': pythonproperties,
        
        }
        
        content += '\n\n'
            
    fp = open(fgdfilename, 'wt')
    fp.write(content)
    fp.close()

from importlib.resources import path
bl_info = {
    "name": "New Object",
    "author": "Your Name Here",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "Addon settings",
    "description": "Asset Manager",
    "warning": "",
    "doc_url": "",
    "category": "Misc",
}


import os, json
from copy import deepcopy
from distutils.dir_util import copy_tree
from shutil import copyfile
import bpy
import bpy.utils.previews


assetPackages = []
# the content of the current asset package
assetPackage = [0]
assetPackagesLookup = {}
imagePreviews = [0]
# a mapping between an asset attribute in a JSON file and the attribute of <BlosmAmProperties>
assetAttr2AmAttr = {
    "category": "assetCategory",
    "type": "type",
    "name": "name",
    "path": "path",
    "part": "part",
    "featureWidthM": "featureWidthM",
    "featureLpx": "featureLpx",
    "featureRpx": "featureRpx",
    "numTilesU": "numTilesU",
    "numTilesV": "numTilesV",
    "material": "claddingMaterial",
    "textureWidthM": "textureWidthM",
    "part": "buildingPart"
}

defaults = dict(
    texture = dict(
        part = dict(
            category = "part",
            part = "level",
            type = "texture",
            featureWidthM = 1.,
            featureLpx = 0,
            featureRpx = 100,
            numTilesU = 2,
            numTilesV = 2
        ),
        cladding = dict(
            category = "cladding",
            type = "texture",
            material = "concrete",
            textureWidthM = 1.
        )
    ),
    mesh = dict()
)


# values for <_changed>:
_edited = 1
_new = 2


# There are no edits if we simply change the selected building assets collection.
# See <updateBuilding(..)>
_ignoreEdits = False


def getAssetsDir(context):
    with open(
        os.path.join( os.path.dirname(os.path.realpath(__file__)), "assets.txt" ),
        'r'
    ) as _file:
        assetsDir = _file.readline().strip()
    return assetsDir


def getBuildingEntry(context):
    return assetPackage[0]["buildings"][int(context.scene.blosmAm.building)]


def getAssetInfo(context):
    return getBuildingEntry(context)["assets"][int(context.scene.blosmAm.buildingAsset)]


def _markBuildingEdited(buildingEntry):
    if _ignoreEdits:
        return
    if not buildingEntry["_changed"]:
        buildingEntry["_changed"] = _edited
    _markAssetPackageChanged()


def _markAssetPackageChanged():
    if not assetPackage[0]["_changed"]:
        assetPackage[0]["_changed"] = 1
    

def updateAttributes(am, assetInfo):
    category = assetInfo["category"]
    am.assetCategory = category
    if category == "part":
        am.buildingPart = assetInfo["part"]
        am.featureWidthM = assetInfo["featureWidthM"]
        am.featureLpx = assetInfo["featureLpx"]
        am.featureRpx = assetInfo["featureRpx"]
        am.numTilesU = assetInfo["numTilesU"]
        am.numTilesV = assetInfo["numTilesV"]
    elif category == "cladding":
        am.claddingMaterial = assetInfo["material"]
        am.textureWidthM = assetInfo["textureWidthM"]


_enumBuildings = []
def getBuildings(self, context):
    _enumBuildings.clear()
    _enumBuildings.extend(
        _getBuildingTuple(bldgIndex, bldg) for bldgIndex,bldg in enumerate(assetPackage[0]["buildings"])
    )
    return _enumBuildings

def _getBuildingTuple(bldgIndex, bldg):
        return (
            str(bldgIndex),
            
            "%s%s" % (
                "[edit] " if bldg["_changed"]==_edited else ("[new] " if bldg["_changed"]==_new else ''),
                bldg["use"],
            ),
            
            bldg["use"]
        )


_enumBuildingAssets = []
def getBuildingAssets(self, context):
    _enumBuildingAssets.clear()
    buildingEntry = getBuildingEntry(context)
    
    # add assets
    loadImagePreviews(buildingEntry["assets"], context)
    _enumBuildingAssets.extend(
        (
            str(assetIndex),
            assetInfo["name"],
            assetInfo["name"],
            imagePreviews[0].get(os.path.join(assetInfo["path"], assetInfo["name"])).icon_id if assetInfo["name"] else "BLANK1",
            # index is required to show the icons
            assetIndex
        ) for assetIndex, assetInfo in enumerate(buildingEntry["assets"])
    )
    return _enumBuildingAssets


class AssetManager:
    
    def draw(self, context):
        layout = self.layout
        am = context.scene.blosmAm
        if not assetPackages:
            layout.operator("blosm.am_load_ap_list")
            return
        
        if am.state == "apNameEditor":
            self.drawApNameEditor(context)
        elif am.state == "apSelection":
            self.drawApSelection(context)
        elif am.state == "apEditor":
            self.drawApEditor(context)
    
    def drawApSelection(self, context):
        layout = self.layout
        am = context.scene.blosmAm
        
        layout.operator("blosm.am_install_asset_package")
        row = layout.row()
        row.prop(am, "assetPackage")
        row.operator("blosm.am_edit_ap", text="Edit package")
        row.operator("blosm.am_copy_ap", text="Copy")
        #row.operator("blosm.am_update_asset_package", text="Update") # TODO
        row.operator("blosm.am_edit_ap_name", text="Edit name")
        row.operator("blosm.am_remove_ap", text="Remove")
        
        #layout.operator("blosm.am_select_building")
    
    def drawApNameEditor(self, context):
        layout = self.layout
        am = context.scene.blosmAm
        
        layout.prop(am, "apDirName")
        layout.prop(am, "apName")
        layout.prop(am, "apDescription")
        
        row = layout.row()
        row.operator("blosm.am_apply_ap_name")
        row.operator("blosm.am_cancel")
    
    def drawApEditor(self, context):
        layout = self.layout
        am = context.scene.blosmAm
        
        row = layout.row()
        row.label(
            text = "Asset package: %s%s" %
            (
                assetPackagesLookup[am.assetPackage][1],
                " [edited]" if assetPackage[0]["_changed"] else ''
            )
        )
        row.operator("blosm.am_save_ap")
        row.operator("blosm.am_cancel")
        
        row = layout.row()
        row.prop(am, "building")
        row2 = row.row(align=True)
        row2.operator("blosm.am_add_building", text='', icon='FILE_NEW')
        row2.operator("blosm.am_delete_building", text='', icon='PANEL_CLOSE')
        
        layout.prop(am, "buildingUse")
        
        assetInfo = getAssetInfo(context)
        
        #layout.prop(am, "buildingAsset")
        box = layout.box()
        
        box.prop(am, "showAdvancedOptions")
        
        assetIconBox = box.box()
        row = assetIconBox.row()
        row.template_icon_view(am, "buildingAsset", show_labels=True)
        if am.showAdvancedOptions:
            column = row.column(align=True)
            column.operator("blosm.am_add_bldg_asset", text='', icon='ADD')
            column.operator("blosm.am_delete_bldg_asset", text='', icon='REMOVE')
        self.drawPath(None, assetIconBox.row(), assetInfo, "path", "name")
        
        box.prop(am, "assetCategory")
        
        if am.assetCategory == "part":
            box.prop(am, "buildingPart")
            box.prop(am, "featureWidthM")
            box.prop(am, "featureLpx")
            box.prop(am, "featureRpx")
            box.prop(am, "numTilesU")
            box.prop(am, "numTilesV")
            
            if am.showAdvancedOptions:
                self.drawPath("Specular map", box.row(), assetInfo, "specularMapPath", "specularMapName")
        elif am.assetCategory == "cladding":
            box.prop(am, "claddingMaterial")
            box.prop(am, "textureWidthM")
    
    def drawPath(self, textureName, rowPath, assetInfo, pathAttr, nameAttr):
        if textureName:
            rowPath.label(text = "%s:" % textureName)
            rowPath.label(text = "%s/%s" % (assetInfo[pathAttr], assetInfo[nameAttr])\
                if assetInfo.get(nameAttr) else\
                "Select an asset:"
            )
        else:
            rowPath.label(text = "Path: %s/%s" % (assetInfo[pathAttr], assetInfo[nameAttr])\
                    if assetInfo.get(nameAttr) else\
                    rowPath.label(text = "Select an asset:")
            )
        op = rowPath.operator("blosm.am_set_asset_path", icon='FILE_FOLDER')
        op.pathAttr = pathAttr
        op.nameAttr = nameAttr


class MyAddonPreferences(bpy.types.AddonPreferences, AssetManager):
    bl_idname = __name__


class BLOSM_PT_Panel(bpy.types.Panel, AssetManager):
    bl_label = "blender-osm"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "asset manager"


_enumAssetPackages = []
def getAssetPackages(self, context):
    _enumAssetPackages.clear()
    _enumAssetPackages.extend(
        (assetPackage[0], assetPackage[1], assetPackage[2]) for assetPackage in assetPackages
    )
    return _enumAssetPackages


def loadImagePreviews(imageList, context):
    for imageEntry in imageList:
        if not imageEntry["name"]:
            return
        # generates a thumbnail preview for a file.
        name = os.path.join(imageEntry["path"], imageEntry["name"])
        filepath = os.path.join(getAssetsDir(context), imageEntry["path"][1:], imageEntry["name"])
        if not imagePreviews[0].get(name) and os.path.isfile(filepath):
            imagePreviews[0].load(name, filepath, 'IMAGE')


#
# Update functions for <bpy.props.EnumProperty> fields
#

def updateBuilding(self, context):
    global _ignoreEdits
    _ignoreEdits = True
    
    buildingEntry = getBuildingEntry(context)
    self.buildingUse = buildingEntry["use"]
    self.buildingAsset = "0"
    
    _ignoreEdits = False
    #updateBuildingAsset(self, context)


def updateBuildingAsset(self, context):
    updateAttributes(
        self,
        getAssetInfo(context)
    )


def _updateAttribute(attr, self, context):
    assetInfo = getAssetInfo(context)
    
    if getattr(self, assetAttr2AmAttr[attr]) != assetInfo[attr]:
        assetInfo[attr] = getattr(self, assetAttr2AmAttr[attr])
        _markBuildingEdited( getBuildingEntry(context) )


def updateBuildingUse(self, context):
    buildingEntry = getBuildingEntry(context)
    
    if self.buildingUse != buildingEntry["use"]:
        buildingEntry["use"] = self.buildingUse
        _markBuildingEdited(buildingEntry)


def updateAssetCategory(self, context):
    assetInfo = getAssetInfo(context)
    
    category = self.assetCategory
    if category != assetInfo["category"]:
        path = assetInfo["path"]
        name = assetInfo["name"]
        assetInfo.clear()
        assetInfo.update(path=path, name=name)
        for a in defaults["texture"][category]:
            value = defaults["texture"][category][a]
            assetInfo[a] = value
            setattr(context.scene.blosmAm, assetAttr2AmAttr[a], value)
        _markBuildingEdited( getBuildingEntry(context) )


def updateBuildingPart(self, context):
    _updateAttribute("part", self, context)

def updateFeatureWidthM(self, context):
    _updateAttribute("featureWidthM", self, context)

def updateFeatureLpx(self, context):
    _updateAttribute("featureLpx", self, context)

def updateFeatureRpx(self, context):
    _updateAttribute("featureRpx", self, context)

def updateNumTilesU(self, context):
    _updateAttribute("numTilesU", self, context)

def updateNumTilesV(self, context):
    _updateAttribute("numTilesV", self, context)

def updateTextureWidthM(self, context):
    _updateAttribute("textureWidthM", self, context)

def updateCladdingMaterial(self, context):
    _updateAttribute("material", self, context)


class BlosmAmProperties(bpy.types.PropertyGroup):
    
    assetPackage: bpy.props.EnumProperty(
        name = "Asset package",
        items = getAssetPackages,
        description = "Asset package for editing"
    )
    
    state: bpy.props.EnumProperty(
        name = "State",
        items = (
            ("apSelection", "asset package selection", "asset package selection"),
            ("apNameEditor", "asset package name editor", "asset package name editor"),
            ("apEditor", "asset package editor", "asset package editor")
        ),
        description = "Asset manager state",
        default = "apEditor" 
    )
    
    #
    # The properties for the asset package name editor
    #
    apDirName: bpy.props.StringProperty(
        name = "Folder",
        description = "Folder name for the asset package, it must be unique among the asset packages"
    )
    
    apName: bpy.props.StringProperty(
        name = "Name",
        description = "Name for the asset package"
    )
    
    apDescription: bpy.props.StringProperty(
        name = "Description",
        description = "Description for the asset package"
    )
    
    showAdvancedOptions: bpy.props.BoolProperty(
        name = "Show advanced options",
        description = "Show advanced options, for example to add an asset for the building asset collection",
        default = False
    )
    
    building: bpy.props.EnumProperty(
        name = "Building asset collection",
        items = getBuildings,
        description = "Building asset collection for editing",
        update = updateBuilding
    )
    
    buildingAsset: bpy.props.EnumProperty(
        name = "Asset entry",
        items = getBuildingAssets,
        description = "Asset entry for the selected building",
        update = updateBuildingAsset
    )
    
    #
    # The properties for editing a building asset collection
    #
    buildingUse: bpy.props.EnumProperty(
        name = "Building use",
        items = (
            ("apartments", "apartments building", "Apartments"),
            ("single_family", "single family house", "Single family house"),
            ("office", "office building", "Office building"),
            ("mall", "mall", "Mall"),
            ("retail", "retail building", "Retail building"),
            ("hotel", "hotel", "Hotel"),
            ("school", "school", "School"),
            ("university", "university", "University"),
            ("any", "any building type", "Any building type")
        ),
        description = "Building usage",
        update = updateBuildingUse
    )
    
    assetCategory: bpy.props.EnumProperty(
        name = "Asset category",
        items = (
            ("part", "building part", "Building part"),
            ("cladding", "cladding", "Facade or roof cladding")
        ),
        description = "Asset category (building part or cladding)",
        update = updateAssetCategory
    )
    
    featureWidthM: bpy.props.FloatProperty(
        name = "Feature width in meters",
        unit = 'LENGTH',
        subtype = 'UNSIGNED',
        default = 1.,
        description = "The width in meters of the texture feature (for example, a window)",
        update = updateFeatureWidthM
    )
    
    featureLpx: bpy.props.IntProperty(
        name = "Feature left coordinate in pixels",
        subtype = 'PIXEL',
        description = "The left coordinate in pixels of the texture feature (for example, a window)",
        update = updateFeatureLpx
    )
    
    featureRpx: bpy.props.IntProperty(
        name = "Feature right coordinate in pixels",
        subtype = 'PIXEL',
        description = "The right coordinate in pixels of the texture feature (for example, a window)",
        update = updateFeatureRpx
    )
    
    numTilesU: bpy.props.IntProperty(
        name = "Number of tiles horizontally",
        subtype = 'UNSIGNED',
        description = "The number of tiles in the texture in the horizontal direction",
        min = 1,
        update = updateNumTilesU
    )
    
    numTilesV: bpy.props.IntProperty(
        name = "Number of tiles vertically",
        subtype = 'UNSIGNED',
        description = "The number of tiles in the texture in the vertical direction",
        min = 1,
        update = updateNumTilesV
    )
    
    claddingMaterial: bpy.props.EnumProperty(
        name = "Material",
        items = (
            ("brick", "brick", "brick"),
            ("plaster", "plaster", "plaster"),
            ("concrete", "concrete", "concrete"),
            ("metal", "metal", "metal"),
            ("glass", "glass", "glass"),
            ("gravel", "gravel", "gravel"),
            ("roof_tiles", "roof tiles", "roof tiles")
        ),
        description = "Material for cladding",
        update = updateCladdingMaterial
    )
    
    textureWidthM: bpy.props.FloatProperty(
        name = "Texture width in meters",
        unit = 'LENGTH',
        subtype = 'UNSIGNED',
        default = 1.,
        description = "The texture width in meters",
        update = updateTextureWidthM
    )
    
    buildingPart: bpy.props.EnumProperty(
        name = "Building part",
        items = (
            ("level", "level", "level"),
            ("curtain_wall", "curtain wall", "curtain wall")
        ),
        description = "Building part",
        update = updateBuildingPart
    )


###################################################
# Operators
###################################################

def writeJson(jsonObj, jsonFilepath):
    with open(jsonFilepath, 'w', encoding='utf-8') as jsonFile:
        json.dump(jsonObj, jsonFile, ensure_ascii=False, indent=4)

def getApListFilepath(context):
    return os.path.join(getAssetsDir(context), "asset_packages.json")


class BLOSM_OT_AmLoadApList(bpy.types.Operator):
    bl_idname = "blosm.am_load_ap_list"
    bl_label = "Load asset package list"
    bl_description = "Load the list of asset packages"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        assetPackages.clear()
        assetPackagesLookup.clear()
        
        assetPackages.extend( self.getApListJson(context)["assetPackages"] )
        assetPackagesLookup.update( (assetPackage[0],assetPackage) for assetPackage in assetPackages )
        
        context.scene.blosmAm.state = "apSelection"
        return {'FINISHED'}
    
    def getApListJson(self, context):
        apListFilepath = getApListFilepath(context)
        
        # check if the file with the list of asset packages exists
        if not os.path.isfile(apListFilepath):
            # create a JSON file with the default list of asset packages
            writeJson(
                dict(assetPackages = [("default", "default", "default asset package")]),
                apListFilepath
            )
        
        with open(apListFilepath, 'r') as jsonFile:
            apListJson = json.load(jsonFile)
        
        return apListJson


class BLOSM_OT_AmEditAp(bpy.types.Operator):
    bl_idname = "blosm.am_edit_ap"
    bl_label = "Edit asset package"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return assetPackagesLookup[context.scene.blosmAm.assetPackage][0] != "default"
    
    def execute(self, context):
        am = context.scene.blosmAm
        
        with open(
            os.path.join(getAssetsDir(context), am.assetPackage, "asset_info", "asset_info.json"),
            'r'
        ) as jsonFile:
            assetPackage[0] = json.load(jsonFile)
        
        assetPackage[0]["_changed"] = 0
        
        # mark all building asset collection as NOT changed
        for buildingEntry in assetPackage[0]["buildings"]:
            buildingEntry["_changed"] = 0
            if not "use" in buildingEntry:
                buildingEntry["use"] = "any"
        
        # set the active building asset collection to element with the index 0
        am.building = "0"
        # pick up the building asset collection with the index 0
        buildingEntry = assetPackage[0]["buildings"][0]
        # pick up the asset info with the index 0
        assetInfo = buildingEntry["assets"][0]
        am.buildingUse = buildingEntry["use"]
        updateAttributes(am, assetInfo)
        
        context.scene.blosmAm.state = "apEditor"
        return {'FINISHED'}


class BLOSM_OT_AmEditApName(bpy.types.Operator):
    bl_idname = "blosm.am_edit_ap_name"
    bl_label = "Edit asset package name"
    bl_options = {'INTERNAL'}
    
    @classmethod
    def poll(cls, context):
        return assetPackagesLookup[context.scene.blosmAm.assetPackage][0] != "default"
    
    def execute(self, context):
        assetPackage = context.scene.blosmAm.assetPackage
        
        apInfo = assetPackagesLookup[assetPackage]
        context.scene.blosmAm.apDirName = assetPackage
        context.scene.blosmAm.apName = apInfo[1]
        context.scene.blosmAm.apDescription = apInfo[2]
        
        context.scene.blosmAm.state = "apNameEditor"
        return {'FINISHED'}


class BLOSM_OT_AmCopyAp(bpy.types.Operator):
    bl_idname = "blosm.am_copy_ap"
    bl_label = "Copy asset package"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        # 'ap' stands for 'asset package'
        apDirName = context.scene.blosmAm.assetPackage
        assetsDir = getAssetsDir(context)
        sourceDir = os.path.join(assetsDir, apDirName)
        # find a name for the target directory
        counter = 1
        while True:
            apDirNameTarget = "%s_%s" % (apDirName, counter)
            targetDir = os.path.realpath( os.path.join(assetsDir, apDirNameTarget) ) 
            if os.path.isdir(targetDir):
                counter += 1
            else:
                break
        apInfo = assetPackagesLookup[apDirName]
        assetPackages.append([apDirNameTarget, "%s (copy)" % apInfo[1], "%s (copy)" % apInfo[2]])
        assetPackagesLookup[apDirNameTarget] = assetPackages[-1]
        writeJson( dict(assetPackages = assetPackages), getApListFilepath(context) )
        context.scene.blosmAm.assetPackage = apDirNameTarget
        # create a directory for the copy of the asset package <assetPackage>
        os.makedirs(targetDir)
        
        self.copyStyle(sourceDir, targetDir)
        
        self.copyAssetInfos(sourceDir, targetDir, apDirName)
        
        context.scene.blosmAm.apDirName = apDirNameTarget
        context.scene.blosmAm.apName = assetPackages[-1][1]
        context.scene.blosmAm.apDescription = assetPackages[-1][2]
        
        context.scene.blosmAm.state = "apNameEditor"
        
        return {'FINISHED'}
    
    def copyStyle(self, sourceDir, targetDir):
        copy_tree(
            os.path.join(sourceDir, "style"),
            os.path.join(targetDir, "style")
        )
    
    def copyAssetInfos(self, sourceDir, targetDir, apDirName):
        os.makedirs( os.path.join(targetDir, "asset_info") )
        # iterate through JSON files in the sub-directory "asset_info" of <sourceDir>
        for fileName in os.listdir( os.path.join(sourceDir, "asset_info") ):
            if os.path.splitext(fileName)[1] == ".json":
                # 'ai' stands for 'asset info'
                aiFilepathSource = os.path.join(sourceDir, "asset_info", fileName)
                aiFilepathTarget = os.path.join(targetDir, "asset_info", fileName)
                # open the source asset info file
                with open(aiFilepathSource, 'r') as aiFile:
                    assetInfos = json.load(aiFile)
                self.processAssetInfos(assetInfos, apDirName)
                # write the target asset info file
                writeJson(assetInfos, aiFilepathTarget)
    
    def processAssetInfos(self, assetInfos, apDirName):
        """
        The method checks every building entry in <assetInfo> and
        then every 'part' in the building entry.
        If the field 'path' doesn't start with /, the prefix apDirName/ is added to the field 'path'
        """
        for bldgEntry in assetInfos["buildings"]:
            for assetInfo in bldgEntry["assets"]:
                path = assetInfo["path"]
                if path[0] != '/':
                    assetInfo["path"] = "/%s/%s" % (apDirName, path)


class BLOSM_OT_AmInstallAssetPackage(bpy.types.Operator):
    bl_idname = "blosm.am_install_asset_package"
    bl_label = "Install"
    bl_description = "Install asset package from a zip-file"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        print("The asset package has been installed")
        return {'FINISHED'}


class BLOSM_OT_AmUpdateAssetPackage(bpy.types.Operator):
    bl_idname = "blosm.am_update_asset_package"
    bl_label = "Update asset package"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        print("The asset package has been updated")
        return {'FINISHED'}


class BLOSM_OT_AmCancel(bpy.types.Operator):
    bl_idname = "blosm.am_cancel"
    bl_label = "Cancel"
    bl_description = "A generic operator for canceling"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        context.scene.blosmAm.state = "apSelection"
        return {'FINISHED'}
    

class BLOSM_OT_AmApplyApName(bpy.types.Operator):
    bl_idname = "blosm.am_apply_ap_name"
    bl_label = "Apply"
    bl_description = "Apply asset package name"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        blosmAm = context.scene.blosmAm
        apDirName = blosmAm.assetPackage
        apInfo = assetPackagesLookup[apDirName]
        
        isDirty = False
        if blosmAm.apDirName != apInfo[0]:
            if blosmAm.apDirName in assetPackagesLookup:
                self.report({'ERROR'}, "The folder '%s' for the asset package already exists" % blosmAm.apDirName)
                return {'CANCELLED'}
            try:
                assetsDir = getAssetsDir(context)
                os.rename(
                    os.path.join(assetsDir, apDirName),
                    os.path.join(assetsDir, blosmAm.apDirName)
                )
            except Exception as _:
                self.report({'ERROR'}, "Unable to create the folder '%s' for the asset package" % blosmAm.apDirName)
                return {'CANCELLED'}
            apInfo[0] = blosmAm.apDirName
            assetPackagesLookup[blosmAm.apDirName] = apInfo
            del assetPackagesLookup[apDirName]
            blosmAm.assetPackage = blosmAm.apDirName
            isDirty = True
        if apInfo[1] != blosmAm.apName:
            apInfo[1] = blosmAm.apName
            isDirty = True
        if apInfo[2] != blosmAm.apDescription:
            apInfo[2] = blosmAm.apDescription
            isDirty = True
        
        if isDirty:
            writeJson (dict(assetPackages = assetPackages), getApListFilepath(context) )
        
        context.scene.blosmAm.state = "apSelection"
        return {'FINISHED'}


class BLOSM_OT_AmRemoveAp(bpy.types.Operator):
    bl_idname = "blosm.am_remove_ap"
    bl_label = "Remove the asset package"
    bl_description = "Remove the asset package from the list. Its folder will remain intact"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return assetPackagesLookup[context.scene.blosmAm.assetPackage][0] != "default"

    def execute(self, context):
        # the directory name of an asset package serves as its id
        apDirName = context.scene.blosmAm.assetPackage
        apInfo = assetPackagesLookup[apDirName]
        del assetPackagesLookup[apDirName]
        assetPackages.remove(apInfo)
        # the asset package <default> is write protected
        context.scene.blosmAm.assetPackage = "default"
        self.report({'INFO'},
            "The asset package \"%s\" has been deleted from the list. Its directory remained intact" % apInfo[1]
        )
        writeJson( dict(assetPackages = assetPackages), getApListFilepath(context) )
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class BLOSM_OT_AmSaveAp(bpy.types.Operator):
    bl_idname = "blosm.am_save_ap"
    bl_label = "Save"
    bl_description = "Save the asset package"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        if not self.validate():
            return {'FINISHED'}
        ap = deepcopy(assetPackage[0])
        self.cleanup(ap, True)
        path = os.path.join(getAssetsDir(context), context.scene.blosmAm.assetPackage, "asset_info", "asset_info.json")
        writeJson(
            ap,
            path
        )
        self.report({'INFO'}, "The asset package has been successfully saved to %s" % path)
        self.cleanup(assetPackage[0], False)
        return {'FINISHED'}
    
    def validate(self):
        ap = assetPackage[0]
        for buildingEntry in ap["buildings"]:
            for assetInfo in buildingEntry["assets"]:
                if not (assetInfo["path"] and assetInfo["name"]):
                    self.report({'ERROR'},
                        "Unable to save: there is at least one asset without a valid path"
                    )
                    return False
        return True
    
    def cleanup(self, ap, deleteChanged):
        if "buildings" in ap:
            for buildingEntry in ap["buildings"]:
                if deleteChanged:
                    del buildingEntry["_changed"]
                else:
                    # just reset it
                    buildingEntry["_changed"] = 0
        if deleteChanged:
            del ap["_changed"]
        else:
            # just reset it
            ap["_changed"] = 0


class BLOSM_OT_AmSelectBuilding(bpy.types.Operator):
    bl_idname = "blosm.am_select_building"
    bl_label = "Select building entry"
    bl_options = {'INTERNAL'}
    bl_property = "buildingList"
    bl_options = {'INTERNAL'}

    buildingList: bpy.props.EnumProperty(
        name = "Building list",
        items = [('one', 'Any', "", 'PRESET', 1), ('two', 'PropertyGroup', "", 'PRESET', 2), ('three', 'type', "", 'PRESET', 3)]
    )
    
    def execute(self, context):
        print(self.buildingList)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}


class BLOSM_OT_AmAddBuilding(bpy.types.Operator):
    bl_idname = "blosm.am_add_building"
    bl_label = "New"
    bl_description = "Add a new building asset collection"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        am = context.scene.blosmAm
        bldgIndex = len(assetPackage[0]["buildings"])
        # Create a building asset collection using the current values of
        # <am.buildingUse>
        assetInfo = defaults["texture"][am.assetCategory].copy()
        assetInfo.update(name = '', path = '')
        buildingEntry = dict(
            use = am.buildingUse,
            assets = [ assetInfo ],
            _changed = _new
        )
        assetPackage[0]["buildings"].append(buildingEntry)
        _enumBuildings.append( _getBuildingTuple(bldgIndex, buildingEntry) )
        am.building = str(bldgIndex)
        
        _markAssetPackageChanged()
        return {'FINISHED'}


class BLOSM_OT_AmDeleteBuilding(bpy.types.Operator):
    bl_idname = "blosm.am_delete_building"
    bl_label = "Delete the building asset collection"
    bl_description = "Delete the building asset collection"
    bl_options = {'INTERNAL'}
    
    showConfirmatioDialog: bpy.props.BoolProperty(
        name = "Show this dialog",
        description = "Show this dialog to confirm the deletion of a building asset collection",
        default = True
    )
    
    def execute(self, context):
        buildingIndex = int(context.scene.blosmAm.building)
        del assetPackage[0]["buildings"][buildingIndex]
        context.scene.blosmAm.building = str(buildingIndex-1)\
            if len(assetPackage[0]["buildings"]) == buildingIndex else\
            context.scene.blosmAm.building
        #updateBuilding(context.scene.blosmAm, context)
        _markAssetPackageChanged()
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if self.showConfirmatioDialog:
            return context.window_manager.invoke_props_dialog(self)
        else:
            return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "showConfirmatioDialog")


class BLOSM_OT_AmAddBldgAsset(bpy.types.Operator):
    bl_idname = "blosm.am_add_bldg_asset"
    bl_label = "Add"
    bl_description = "Add a building asset"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        am = context.scene.blosmAm
        buildingEntry = getBuildingEntry(context)
        
        assetIndex = len(buildingEntry["assets"])
        assetInfo = defaults["texture"][am.assetCategory].copy()
        assetInfo.update(name = '', path = '')
        buildingEntry["assets"].append(assetInfo)
        
        _enumBuildingAssets.append( (str(assetIndex), '', '', "BLANK1", assetIndex) )
        am.buildingAsset = str(assetIndex)
        
        _markBuildingEdited(buildingEntry)
        return {'FINISHED'}


class BLOSM_OT_AmDeleteBldgAsset(bpy.types.Operator):
    bl_idname = "blosm.am_delete_bldg_asset"
    bl_label = "Delete"
    bl_description = "Delete the building asset"
    bl_options = {'INTERNAL'}
    
    @classmethod
    def poll(cls, context):
        return len(getBuildingEntry(context)["assets"]) > 1
    
    def execute(self, context):
        buildingEntry = getBuildingEntry(context)
        assetIndex = int(context.scene.blosmAm.buildingAsset)
        
        del buildingEntry["assets"][assetIndex]
        
        context.scene.blosmAm.building = "0"
            
        _markBuildingEdited(buildingEntry)
        return {'FINISHED'}


class BLOSM_OT_AmSetAssetPath(bpy.types.Operator):
    bl_idname = "blosm.am_set_asset_path"
    bl_label = "Set path..."
    bl_description = "Set path to the asset"
    bl_options = {'INTERNAL'}
    
    filename: bpy.props.StringProperty()
    
    directory: bpy.props.StringProperty(
        subtype = 'FILE_PATH'
    )
    
    pathAttr: bpy.props.StringProperty()
    
    nameAttr: bpy.props.StringProperty()
    
    def execute(self, context):
        assetsDir = os.path.normpath(getAssetsDir(context))
        directory = os.path.normpath(self.directory)
        
        name = self.filename
        
        if directory.startswith(assetsDir):
            lenAssetsDir = len(assetsDir)
            if lenAssetsDir == len(directory):
                self.report({'ERROR'}, "The asset must be located in the folder of an asset package")
            else:
                self.setAssetPath(
                    context,
                    "/".join( directory[lenAssetsDir:].split(os.sep) ),
                    name
                )    
        else:
            path = os.path.join(
                getAssetsDir(context),
                context.scene.blosmAm.assetPackage,
                "assets"
            )
            # The asset will be moved to the directory <path>
            if os.path.isfile( os.path.join(path, name) ):
                self.report({'INFO'},
                    ("The existing asset %s in the sub-bolder \"%s\" in your directory for assets " +\
                    "will be used instead of the selected asset.") % (name, path)
                )
            else:
                if not os.path.isdir(path):
                    os.makedirs(path)
                copyfile(
                    os.path.join(directory, name),
                    os.path.join(path, name)
                )
                self.report({'INFO'},
                    "The asset has been copied to the sub-folder \"%s\" in your directory for assets" %
                    os.path.join(context.scene.blosmAm.assetPackage, "assets")
                )
            self.setAssetPath(
                context,
                "/%s" % '/'.join( (context.scene.blosmAm.assetPackage, "assets") ),
                name
            )
            
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def setAssetPath(self, context, path, name):
        assetInfo = getAssetInfo(context)
        if path != assetInfo.get(self.pathAttr) or name != assetInfo.get(self.nameAttr):
            assetInfo[self.pathAttr] = path
            assetInfo[self.nameAttr] = name
            _markBuildingEdited(getBuildingEntry(context))


###################################################
# Registration
###################################################

_classes = (
    MyAddonPreferences,
    BLOSM_PT_Panel,
    BlosmAmProperties,
    BLOSM_OT_AmLoadApList,
    BLOSM_OT_AmEditAp,
    BLOSM_OT_AmEditApName,
    BLOSM_OT_AmCopyAp,
    BLOSM_OT_AmInstallAssetPackage,
    BLOSM_OT_AmUpdateAssetPackage,
    BLOSM_OT_AmCancel,
    BLOSM_OT_AmApplyApName,
    BLOSM_OT_AmRemoveAp,
    BLOSM_OT_AmSaveAp,
    BLOSM_OT_AmSelectBuilding,
    BLOSM_OT_AmAddBuilding,
    BLOSM_OT_AmDeleteBuilding,
    BLOSM_OT_AmAddBldgAsset,
    BLOSM_OT_AmDeleteBldgAsset,
    BLOSM_OT_AmSetAssetPath
)

def register():
    for _class in _classes:
        bpy.utils.register_class(_class)
    
    bpy.types.Scene.blosmAm = bpy.props.PointerProperty(type=BlosmAmProperties)
    
    imagePreviews[0] = bpy.utils.previews.new()


def unregister():
    for _class in _classes:
        bpy.utils.unregister_class(_class)
    
    del bpy.types.Scene.blosmAm
    
    imagePreviews[0].close()
    imagePreviews.clear()


if __name__ == "__main__":
    register()

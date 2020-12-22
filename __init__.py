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
    "featureWidthM": "featureWidthM",
    "featureLpx": "featureLpx",
    "featureRpx": "featureRpx",
    "numTilesU": "numTilesU",
    "numTilesV": "numTilesV",
    "material": "material",
    "textureWidthM": "textureWidthM"
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
            numTilesV = 2,
            name = '',
            path = ''
        ),
        cladding = dict(
            category = "cladding",
            type = "texture",
            material = "concrete",
            textureWidthM = 1.,
            name = '',
            path = '' 
        )
    ),
    mesh = dict()
)


def getAssetsDir(context):
    return "D:\\projects\\prokitektura\\tmp\\premium\\assets"


def getBuildingEntry(context):
    return assetPackage[0]["buildings"][int(context.scene.blosmAm.building)]


def getAssetInfo(context):
    return getBuildingEntry(context)["assets"][int(context.scene.blosmAm.buildingAsset)]
    

def updateAttributes(am, assetInfo):
    category = assetInfo["category"]
    am.assetCategory = category
    if category == "part":
        am.featureWidthM = assetInfo["featureWidthM"]
        am.featureLpx = assetInfo["featureLpx"]
        am.featureRpx = assetInfo["featureRpx"]
        am.numTilesU = assetInfo["numTilesU"]
        am.numTilesV = assetInfo["numTilesV"]
    elif category == "cladding":
        am.textureWidthM = assetInfo["textureWidthM"]


_enumBuildings = []
def getBuildings(self, context):
    _enumBuildings.clear()
    _enumBuildings.extend(
        (
            str(bldgIndex),
            
            "%s%s" % (
                "* " if bldg.get("_dirty") else '',
                bldg["use"],
            ),
            
            bldg["use"]
        ) for bldgIndex,bldg in enumerate(assetPackage[0]["buildings"])
    )
    return _enumBuildings


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
            imagePreviews[0].get(os.path.join(assetInfo["path"], assetInfo["name"])).icon_id if assetInfo["name"] else 0,
            # index is required to show the icons
            assetIndex
        ) for assetIndex, assetInfo in enumerate(buildingEntry["assets"])
    )
    return _enumBuildingAssets


import os
import bpy
import bpy.utils.previews
from .operator import register as operatorRegister
from .operator import unregister as operatorUnregister


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
        row.operator("blosm.am_update_asset_package", text="Update")
        row.operator("blosm.am_edit_ap_name", text="Edit name")
        row.operator("blosm.am_delete_ap", text="Delete")
        
        layout.operator("blosm.am_select_building")
    
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
        row.label(text=assetPackagesLookup[am.assetPackage][1])
        row.operator("blosm.am_save_ap")
        row.operator("blosm.am_cancel")
        
        row = layout.row()
        row.prop(am, "building")
        row2 = row.row(align=True)
        row2.operator("blosm.am_add_building", text='', icon='FILE_NEW')
        row2.operator("blosm.am_delete_building", text='', icon='PANEL_CLOSE')
        
        layout.prop(am, "buildingUse")
        
        #layout.prop(am, "buildingAsset")
        box = layout.box()
        
        assetInfo = getAssetInfo(context)
        
        row = box.row()
        if assetInfo["name"]:
            row.template_icon_view(am, "buildingAsset", show_labels=True)
            if am.showAdvancedOptions:
                column = row.column(align=True)
                column.operator("blosm.am_add_bldg_asset", text='', icon='ADD')
                column.operator("blosm.am_delete_bldg_asset", text='', icon='REMOVE')
            box.prop(am, "showAdvancedOptions")
            rowPath = box.row()
            rowPath.label(text = "Path: %s/%s" % (assetInfo["path"], assetInfo["name"]))
            rowPath.operator("blosm.am_set_asset_path", icon='FILE_FOLDER')
        
        box.prop(am, "assetCategory")
        
        if am.assetCategory == "part":
            box.prop(am, "featureWidthM")
            box.prop(am, "featureLpx")
            box.prop(am, "featureRpx")
            box.prop(am, "numTilesU")
            box.prop(am, "numTilesV")
        elif am.assetCategory == "cladding":
            layout.prop(am, "textureWidthM")


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
    buildingEntry = getBuildingEntry(context)
    self.buildingUse = buildingEntry["use"]
    self.buildingAsset = "0"
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
        _markDirty( getBuildingEntry(context) )


def _markDirty(buildingEntry):
    if not buildingEntry["_dirty"]:
        buildingEntry["_dirty"] = True


def updateBuildingUse(self, context):
    buildingEntry = getBuildingEntry(context)
    
    if self.buildingUse != buildingEntry["use"]:
        buildingEntry["use"] = self.buildingUse
        if not buildingEntry["_dirty"]:
            buildingEntry["_dirty"] = True


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
        _markDirty( getBuildingEntry(context) )


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
    
    textureWidthM: bpy.props.FloatProperty(
        name = "Texture width in meters",
        unit = 'LENGTH',
        subtype = 'UNSIGNED',
        default = 1.,
        description = "The texture width in meters",
        update = updateTextureWidthM
    )

# Registration

def register():
    bpy.utils.register_class(MyAddonPreferences)
    bpy.utils.register_class(BLOSM_PT_Panel)
    bpy.utils.register_class(BlosmAmProperties)
    operatorRegister()
    bpy.types.Scene.blosmAm = bpy.props.PointerProperty(type=BlosmAmProperties)
    imagePreviews[0] = bpy.utils.previews.new()


def unregister():
    del bpy.types.Scene.blosmAm
    bpy.utils.unregister_class(MyAddonPreferences)
    bpy.utils.unregister_class(BLOSM_PT_Panel)
    bpy.utils.unregister_class(BlosmAmProperties)
    operatorUnregister()
    imagePreviews[0].close()
    imagePreviews.clear()


if __name__ == "__main__":
    register()

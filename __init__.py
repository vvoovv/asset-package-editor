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
assetInfo = [0]
assetPackagesLookup = {}
imagePreviews = [0]

def getAssetsDir(context):
    return "D:\\projects\\prokitektura\\tmp\\premium\\assets"


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
        #layout.prop(am, "buildingAsset")
        box = layout.box()
        row = box.row()
        row.template_icon_view(am, "buildingAsset", show_labels=True)
        
        if am.showAdvancedOptions:
            column = row.column(align=True)
            column.operator("blosm.am_add_bldg_asset", text='', icon='ADD')
            column.operator("blosm.am_delete_bldg_asset", text='', icon='REMOVE')
        
        box.prop(am, "showAdvancedOptions")


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


_enumBuildings = []
def getBuildings(self, context):
    _enumBuildings.clear()
    _enumBuildings.extend(
        (str(bldgIndex), bldg["use"] if "use" in bldg else "any", bldg["use"] if "use" in bldg else "any") for bldgIndex,bldg in enumerate(assetInfo[0]["buildings"])
    )
    return _enumBuildings


_enumBuildingAssets = []
def getBuildingAssets(self, context):
    _enumBuildingAssets.clear()
    buildingEntry = assetInfo[0]["buildings"][int(context.scene.blosmAm.building)]
    
    # add building parts
    if "parts" in buildingEntry:
        loadImagePreviews(buildingEntry["parts"], context)
        # <p> stands for 'part'
        _enumBuildingAssets.extend(
            (
                "p%s" % partIndex,
                part["name"],
                part["name"],
                imagePreviews[0].get(os.path.join(part["path"], part["name"])).icon_id,
                # index is required to show the icons
                partIndex
            ) for partIndex, part in enumerate(buildingEntry["parts"])
        )
    # add building cladding
    if "cladding" in buildingEntry:
        loadImagePreviews(buildingEntry["cladding"], context)
        # <c> stands for 'cladding'
        _enumBuildingAssets.extend(
            (
                "c%s" % claddingIndex,
                cladding["name"],
                cladding["name"],
                imagePreviews[0].get(os.path.join(cladding["path"], cladding["name"])).icon_id,
                # index is required to show the icons
                claddingIndex
            ) for claddingIndex, cladding in enumerate(buildingEntry["cladding"])
        )
    return _enumBuildingAssets


def loadImagePreviews(imageList, context):
    for imageEntry in imageList:
        # generates a thumbnail preview for a file.
        name = os.path.join(imageEntry["path"], imageEntry["name"])
        filepath = os.path.join(getAssetsDir(context), imageEntry["path"][1:], imageEntry["name"])
        if not imagePreviews[0].get(name) and os.path.isfile(filepath):
            imagePreviews[0].load(name, filepath, 'IMAGE')


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
        description = "Building asset collection for editing"
    )
    
    buildingAsset: bpy.props.EnumProperty(
        name = "Asset entry",
        items = getBuildingAssets,
        description = "Asset entry for the selected building"
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

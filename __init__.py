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


import bpy
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
        
        layout.label(text=am.assetPackage)
        layout.prop(am, "building")


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
    
    building: bpy.props.EnumProperty(
        name = "Building entry",
        items = getBuildings,
        description = "Building entry for editing"
    )


# Registration

def register():
    bpy.utils.register_class(MyAddonPreferences)
    bpy.utils.register_class(BLOSM_PT_Panel)
    bpy.utils.register_class(BlosmAmProperties)
    operatorRegister()
    bpy.types.Scene.blosmAm = bpy.props.PointerProperty(type=BlosmAmProperties)


def unregister():
    del bpy.types.Scene.blosmAm
    bpy.utils.unregister_class(MyAddonPreferences)
    bpy.utils.unregister_class(BLOSM_PT_Panel)
    bpy.utils.unregister_class(BlosmAmProperties)
    operatorUnregister()


if __name__ == "__main__":
    register()

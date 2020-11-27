import os, json
from copy import deepcopy
from distutils.dir_util import copy_tree
import bpy


from . import assetPackages, assetInfo, assetPackagesLookup, getAssetsDir


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
    
    def execute(self, context):
        assetPackage = context.scene.blosmAm.assetPackage
        
        with open(
            os.path.join(getAssetsDir(context), assetPackage, "asset_info", "asset_info.json"),
            'r'
        ) as jsonFile:
            assetInfo[0] = json.load(jsonFile)
        
        context.scene.blosmAm.state = "apEditor"
        return {'FINISHED'}


class BLOSM_OT_AmEditApName(bpy.types.Operator):
    bl_idname = "blosm.am_edit_ap_name"
    bl_label = "Edit asset package name"
    bl_options = {'INTERNAL'}
    
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
        assetPackages.append((apDirNameTarget, "%s (copy)" % apInfo[1], "%s (copy)" % apInfo[2]))
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
                    assetInfo = deepcopy(json.load(aiFile))
                self.processAssetInfo(assetInfo, apDirName)
                # write the target asset info file
                writeJson(assetInfo, aiFilepathTarget)
    
    def processAssetInfo(self, assetInfo, apDirName):
        """
        The method checks every building entry in <assetInfo> and
        then every 'part' in the building entry.
        If the field 'path' doesn't start with /, the prefix apDirName/ is added to the field 'path'
        """
        for bldgEntry in assetInfo["buildings"]:
            self.processAssetInfoList("parts", bldgEntry, apDirName)
            self.processAssetInfoList("cladding", bldgEntry, apDirName)
        
    def processAssetInfoList(self, listName, bldgEntry, apDirName):
        if listName in bldgEntry:
            for listEntry in bldgEntry[listName]:
                path = listEntry["path"]
                if path[0] != '/':
                    listEntry["path"] = "/%s/%s" % (apDirName, path)


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


class BLOSM_OT_AmDeleteAp(bpy.types.Operator):
    bl_idname = "blosm.am_delete_ap"
    bl_label = "Delete asset package"
    bl_description = "Delete asset package"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        print("Deleted")
        return {'FINISHED'}


class BLOSM_OT_AmSaveAp(bpy.types.Operator):
    bl_idname = "blosm.am_save_ap"
    bl_label = "Save"
    bl_description = "Save the asset package"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        print("Save")
        return {'FINISHED'}


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
    bl_label = "Add"
    bl_description = "Add a building asset collection"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        print("Added")
        return {'FINISHED'}


class BLOSM_OT_AmDeleteBuilding(bpy.types.Operator):
    bl_idname = "blosm.am_delete_building"
    bl_label = "Delete"
    bl_description = "Delete the building asset collection"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        print("Deleted")
        return {'FINISHED'}


class BLOSM_OT_AmAddBldgAsset(bpy.types.Operator):
    bl_idname = "blosm.am_add_bldg_asset"
    bl_label = "Add"
    bl_description = "Add a building asset"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        print("Added")
        return {'FINISHED'}


class BLOSM_OT_AmDeleteBldgAsset(bpy.types.Operator):
    bl_idname = "blosm.am_delete_bldg_asset"
    bl_label = "Delete"
    bl_description = "Delete the building asset"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        print("Deleted")
        return {'FINISHED'}


_classes = (
    BLOSM_OT_AmLoadApList,
    BLOSM_OT_AmEditAp,
    BLOSM_OT_AmEditApName,
    BLOSM_OT_AmCopyAp,
    BLOSM_OT_AmInstallAssetPackage,
    BLOSM_OT_AmUpdateAssetPackage,
    BLOSM_OT_AmCancel,
    BLOSM_OT_AmApplyApName,
    BLOSM_OT_AmDeleteAp,
    BLOSM_OT_AmSaveAp,
    BLOSM_OT_AmSelectBuilding,
    BLOSM_OT_AmAddBuilding,
    BLOSM_OT_AmDeleteBuilding,
    BLOSM_OT_AmAddBldgAsset,
    BLOSM_OT_AmDeleteBldgAsset
)


def register():
    for _class in _classes:
        bpy.utils.register_class(_class)
    

def unregister():
    for _class in _classes:
        bpy.utils.unregister_class(_class)
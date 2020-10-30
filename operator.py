import os, json
from copy import deepcopy
from distutils.dir_util import copy_tree
import bpy


from . import assetPackages


def _getAssetsDir(context):
    return "D:\\projects\\prokitektura\\tmp\\premium\\assets"


def writeJson(jsonObj, jsonFilepath):
    with open(jsonFilepath, 'w', encoding='utf-8') as jsonFile:
        json.dump(jsonObj, jsonFile, ensure_ascii=False, indent=4)


class BLOSM_OT_AmLoadApList(bpy.types.Operator):
    bl_idname = "blosm.am_load_ap_list"
    bl_label = "Load asset package list"
    bl_description = "Load the list of asset packages"
    bl_options = {'INTERNAL'}
    
    apListFileName = "asset_packages.json"
    
    def execute(self, context):
        assetPackages.clear()
        assetPackages.extend( self.getApListJson(context)["assetPackages"] )
        context.scene.blosmAm.state = "apSelection"
        return {'FINISHED'}
    
    def getApListJson(self, context):
        apListFilepath = os.path.join(_getAssetsDir(context), self.apListFileName)
        
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
        
            


class BLOSM_OT_AmEditAssetPackage(bpy.types.Operator):
    bl_idname = "blosm.am_edit_asset_package"
    bl_label = "Load asset info"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        assetPackage = context.scene.blosmAm.assetPackage
        print(assetPackage)
        return {'FINISHED'}


class BLOSM_OT_AmEditApName(bpy.types.Operator):
    bl_idname = "blosm.am_edit_ap_name"
    bl_label = "Load asset info"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        assetPackage = context.scene.blosmAm.assetPackage
        
        context.scene.blosmAm.apDirName = assetPackage
        context.scene.blosmAm.apName = "Name"
        context.scene.blosmAm.apDescription = "Description"
        
        context.scene.blosmAm.state = "apNameEditor"
        return {'FINISHED'}


class BLOSM_OT_AmCopyAssetPackage(bpy.types.Operator):
    bl_idname = "blosm.am_copy_asset_package"
    bl_label = "Copy asset package"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        # 'ap' stands for 'asset package'
        apDirName = context.scene.blosmAm.assetPackage
        assetsDir = _getAssetsDir(context)
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
        assetPackages.append((apDirNameTarget, apDirNameTarget, apDirNameTarget))
        context.scene.blosmAm.assetPackage = apDirNameTarget
        # create a directory for the copy of the asset package <assetPackage>
        os.makedirs(targetDir)
        
        self.copyStyle(sourceDir, targetDir)
        
        self.copyAssetInfos(sourceDir, targetDir, apDirName)
        
        context.scene.blosmAm.apDirName = apDirNameTarget
        context.scene.blosmAm.apName = "Name"
        context.scene.blosmAm.apDescription = "Description"
        
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
    

class BLOSM_OT_AmApplyAssetPackageName(bpy.types.Operator):
    bl_idname = "blosm.am_apply_asset_package_name"
    bl_label = "Apply"
    bl_description = "Apply asset package name"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        print("Applied")
        return {'FINISHED'}

_classes = (
    BLOSM_OT_AmLoadApList,
    BLOSM_OT_AmEditAssetPackage,
    BLOSM_OT_AmEditApName,
    BLOSM_OT_AmCopyAssetPackage,
    BLOSM_OT_AmInstallAssetPackage,
    BLOSM_OT_AmUpdateAssetPackage,
    BLOSM_OT_AmCancel,
    BLOSM_OT_AmApplyAssetPackageName
)


def register():
    for _class in _classes:
        bpy.utils.register_class(_class)
    

def unregister():
    for _class in _classes:
        bpy.utils.unregister_class(_class)
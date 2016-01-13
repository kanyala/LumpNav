import os
from __main__ import vtk, qt, ctk, slicer

from Guidelet import GuideletLoadable, GuideletLogic, GuideletTest, GuideletWidget
from Guidelet import Guidelet
import logging
import time
import math

#
# LumpNav ###
#

class LumpNav(GuideletLoadable):
  """Uses GuideletLoadable class, available at:
  """

  def __init__(self, parent):
    GuideletLoadable.__init__(self, parent)
    self.parent.title = "Lumpectomy Navigation"
    self.parent.categories = ["IGT"]
    self.parent.dependencies = []
    self.parent.contributors = ["Tamas Ungi (Perk Lab)"]
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.    

#
# LumpNavWidget
#

class LumpNavWidget(GuideletWidget):
  """Uses GuideletWidget base class, available at:
  """

  def __init__(self, parent = None):
    GuideletWidget.__init__(self, parent)
    
  def setup(self):
    GuideletWidget.setup(self)

  def addLauncherWidgets(self):
    GuideletWidget.addLauncherWidgets(self)

    # BreachWarning
    self.addBreachWarningLightPreferences()

  def onConfigurationChanged(self, selectedConfigurationName):
    GuideletWidget.onConfigurationChanged(self, selectedConfigurationName)
    settings = slicer.app.userSettings()
    lightEnabled = settings.value(self.moduleName + '/Configurations/' + self.selectedConfigurationName + '/EnableBreachWarningLight')
    self.breachWarningLightCheckBox.checked = (lightEnabled == 'True')

  def addBreachWarningLightPreferences(self):
    lnNode = slicer.util.getNode(self.moduleName)
    
    self.breachWarningLightCheckBox = qt.QCheckBox()
    checkBoxLabel = qt.QLabel()
    hBoxCheck = qt.QHBoxLayout()
    hBoxCheck.setAlignment(0x0001)
    checkBoxLabel.setText("Use Breach Warning Light: ")
    hBoxCheck.addWidget(checkBoxLabel)
    hBoxCheck.addWidget(self.breachWarningLightCheckBox)
    hBoxCheck.setStretch(1,2)
    self.launcherFormLayout.addRow(hBoxCheck)

    if(lnNode is not None and lnNode.GetParameter('EnableBreachWarningLight')):
        # logging.debug("There is already a connector EnableBreachWarningLight parameter " + lnNode.GetParameter('EnableBreachWarningLight'))
        self.breachWarningLightCheckBox.checked = lnNode.GetParameter('EnableBreachWarningLight')
        self.breachWarningLightCheckBox.setDisabled(True)
    else:
        self.breachWarningLightCheckBox.setEnabled(True)
        settings = slicer.app.userSettings()
        lightEnabled = settings.value(self.moduleName + '/Configurations/' + self.selectedConfigurationName + '/EnableBreachWarningLight', 'True')
        self.breachWarningLightCheckBox.checked = (lightEnabled == 'True')
        
    self.breachWarningLightCheckBox.connect('stateChanged(int)', self.onBreachWarningLightChanged)
  
  def onBreachWarningLightChanged(self, state):    
    lightEnabled = ''
    if self.breachWarningLightCheckBox.checked:
      lightEnabled = 'True'
    elif not self.breachWarningLightCheckBox.checked:
      lightEnabled = 'False'
    self.guideletLogic.updateSettings({'EnableBreachWarningLight' : lightEnabled}, self.selectedConfigurationName)

  def createGuideletInstance(self):
    return LumpNavGuidelet(None, self.guideletLogic, self.selectedConfigurationName)

  def createGuideletLogic(self):
    return LumpNavLogic()

#
# LumpNavLogic ###
#

class LumpNavLogic(GuideletLogic):
  """Uses GuideletLogic base class, available at:
  """ #TODO add path

  def __init__(self, parent = None):
    GuideletLogic.__init__(self, parent)

  def addValuesToDefaultConfiguration(self):
    GuideletLogic.addValuesToDefaultConfiguration(self)
    moduleDir = os.path.dirname(slicer.modules.lumpnav.path)
    defaultSavePathOfLumpNav = os.path.join(moduleDir, 'SavedScenes')
    settingList = {'EnableBreachWarningLight' : 'False',
                   'BreachWarningLightMarginSizeMm' : '2.0',
                   'TipToSurfaceDistanceTextScale' : '3',
                   'TipToSurfaceDistanceTrajectory' : 'True',
                   'NeedleModelToNeedleTip' : '0 1 0 0 0 0 1 0 1 0 0 0 0 0 0 1',
                   'NeedleBaseToNeedle' : '1 0 0 20.93 0 1 0 -6.00 0 0 1 -4.27 0 0 0 1',
                   'CauteryModelToCauteryTip' : '0 0 1 0 0 -1 0 0 1 0 0 0 0 0 0 1',
                   'PivotCalibrationErrorThresholdMm' :  '0.9',
                   'PivotCalibrationDurationSec' : '5',
                   'TestMode' : 'False',
                   'RecordingFilenamePrefix' : 'LumpNavRecording-',
                   'SavedScenesDirectory': defaultSavePathOfLumpNav,#overwrites the default setting param of base
                   }
    self.updateSettings(settingList, 'Default')


#
#	LumpNavTest ###
#

class LumpNavTest(GuideletTest):
  """This is the test case for your scripted module.
  """
  
  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    GuideletTest.runTest(self)
    #self.test_LumpNav1() #add applet specific tests here

class LumpNavGuidelet(Guidelet):

  def __init__(self, parent, logic, configurationName='Default'):
    Guidelet.__init__(self, parent, logic, configurationName)
    logging.debug('LumpNavGuidelet.__init__')

    moduleDirectoryPath = slicer.modules.lumpnav.path.replace('LumpNav.py', '')

    # Set up main frame.

    self.sliceletDockWidget.setObjectName('LumpNavPanel')
    self.sliceletDockWidget.setWindowTitle('LumpNav')
    self.mainWindow.setWindowTitle('Lumpectomy navigation')
    self.mainWindow.windowIcon = qt.QIcon(moduleDirectoryPath + '/Resources/Icons/LumpNav.png')
    
    self.pivotCalibrationLogic=slicer.modules.pivotcalibration.logic()
    
    # Set needle and cautery transforms and models
    self.tumorMarkups_Needle = None
    self.tumorMarkups_NeedleObserver = None
    self.setupScene()

    # Setting button open on startup.
    self.calibrationCollapsibleButton.setProperty('collapsed', False)

  def createFeaturePanels(self):
    # Create GUI panels.

    self.calibrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.setupCalibrationPanel()
    
    featurePanelList = Guidelet.createFeaturePanels(self)
    self.addTumorContouringToUltrasoundPanel()
    
    self.navigationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.setupNavigationPanel()

    featurePanelList[len(featurePanelList):] = [self.calibrationCollapsibleButton, self.navigationCollapsibleButton]

    return featurePanelList

  def __del__(self):#common
    self.cleanup()

  # Clean up when slicelet is closed
  def cleanup(self):#common
    Guidelet.cleanup(self)
    logging.debug('cleanup')
    self.breachWarningNode.UnRegister(slicer.mrmlScene)
    self.setAndObserveTumorMarkupsNode(None)
    self.breachWarningLightLogic.stopLightFeedback()
    
  def setupConnections(self):
    logging.debug('LumpNav.setupConnections()')
    Guidelet.setupConnections(self)

    self.calibrationCollapsibleButton.connect('toggled(bool)', self.onCalibrationPanelToggled)
    self.navigationCollapsibleButton.connect('toggled(bool)', self.onNavigationPanelToggled)

    self.cauteryPivotButton.connect('clicked()', self.onCauteryPivotClicked)
    self.needlePivotButton.connect('clicked()', self.onNeedlePivotClicked)
    self.needleLengthSpinBox.connect('valueChanged(int)', self.onNeedleLengthModified)
    self.placeButton.connect('clicked(bool)', self.onPlaceClicked)
    self.deleteLastFiducialButton.connect('clicked()', self.onDeleteLastFiducialClicked)
    self.deleteLastFiducialDuringNavigationButton.connect('clicked()', self.onDeleteLastFiducialClicked)    
    self.deleteAllFiducialsButton.connect('clicked()', self.onDeleteAllFiducialsClicked)
    
    self.rightCameraButton.connect('clicked()', self.onRightCameraButtonClicked)
    self.leftCameraButton.connect('clicked()', self.onLeftCameraButtonClicked)

    self.placeTumorPointAtCauteryTipButton.connect('clicked(bool)', self.onPlaceTumorPointAtCauteryTipClicked)

    self.pivotSamplingTimer.connect('timeout()',self.onPivotSamplingTimeout)

    import Viewpoint
    self.viewpointLogic = Viewpoint.ViewpointLogic()
    self.cameraViewAngleSlider.connect('valueChanged(double)', self.viewpointLogic.SetCameraViewAngleDeg)
    self.cameraXPosSlider.connect('valueChanged(double)', self.viewpointLogic.SetCameraXPosMm)
    self.cameraYPosSlider.connect('valueChanged(double)', self.viewpointLogic.SetCameraYPosMm)
    self.cameraZPosSlider.connect('valueChanged(double)', self.viewpointLogic.SetCameraZPosMm)    
    
  def setupScene(self): #applet specific
    logging.debug('setupScene')
    Guidelet.setupScene(self)

    logging.debug('Create transforms')

    self.cauteryTipToCautery = slicer.util.getNode('CauteryTipToCautery')
    if not self.cauteryTipToCautery:
      self.cauteryTipToCautery=slicer.vtkMRMLLinearTransformNode()
      self.cauteryTipToCautery.SetName("CauteryTipToCautery")
      m = self.logic.readTransformFromSettings('CauteryTipToCautery', self.configurationName) 
      if m:
        self.cauteryTipToCautery.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.cauteryTipToCautery)

    self.cauteryModelToCauteryTip = slicer.util.getNode('CauteryModelToCauteryTip')
    if not self.cauteryModelToCauteryTip:
      self.cauteryModelToCauteryTip=slicer.vtkMRMLLinearTransformNode()
      self.cauteryModelToCauteryTip.SetName("CauteryModelToCauteryTip")
      m = self.logic.readTransformFromSettings('CauteryModelToCauteryTip', self.configurationName) 
      if m:
        self.cauteryModelToCauteryTip.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.cauteryModelToCauteryTip)

    self.needleTipToNeedle = slicer.util.getNode('NeedleTipToNeedle')
    if not self.needleTipToNeedle:
      self.needleTipToNeedle=slicer.vtkMRMLLinearTransformNode()
      self.needleTipToNeedle.SetName("NeedleTipToNeedle")
      m = self.logic.readTransformFromSettings('NeedleTipToNeedle', self.configurationName) 
      if m:
        self.needleTipToNeedle.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.needleTipToNeedle)

    self.needleBaseToNeedle = slicer.util.getNode('NeedleBaseToNeedle')
    if not self.needleBaseToNeedle:
      self.needleBaseToNeedle=slicer.vtkMRMLLinearTransformNode()
      self.needleBaseToNeedle.SetName("NeedleBaseToNeedle")
      m = self.logic.readTransformFromSettings('NeedleBaseToNeedle', self.configurationName) 
      if m:
        self.needleBaseToNeedle.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.needleBaseToNeedle)
    
    # Update the displayed needle length based on NeedleTipToNeedle and NeedleTipToNeedleBase
    self.updateDisplayedNeedleLength()
      
    self.needleModelToNeedleTip = slicer.util.getNode('NeedleModelToNeedleTip')
    if not self.needleModelToNeedleTip:
      self.needleModelToNeedleTip=slicer.vtkMRMLLinearTransformNode()
      self.needleModelToNeedleTip.SetName("NeedleModelToNeedleTip")
      m = self.logic.readTransformFromSettings('NeedleModelToNeedleTip', self.configurationName) 
      if m:
        self.needleModelToNeedleTip.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.needleModelToNeedleTip)

    self.cauteryCameraToCautery = slicer.util.getNode('CauteryCameraToCautery')
    if not self.cauteryCameraToCautery:
      self.cauteryCameraToCautery=slicer.vtkMRMLLinearTransformNode()
      self.cauteryCameraToCautery.SetName("CauteryCameraToCautery")
      m = vtk.vtkMatrix4x4()
      m.SetElement( 0, 0, 0 )
      m.SetElement( 0, 2, -1 )
      m.SetElement( 1, 1, 0 )
      m.SetElement( 1, 0, 1 )
      m.SetElement( 2, 2, 0 )
      m.SetElement( 2, 1, -1 )
      self.cauteryCameraToCautery.SetMatrixTransformToParent(m)
      slicer.mrmlScene.AddNode(self.cauteryCameraToCautery)

    self.CauteryToNeedle = slicer.util.getNode('CauteryToNeedle')
    if not self.CauteryToNeedle:
      self.CauteryToNeedle=slicer.vtkMRMLLinearTransformNode()
      self.CauteryToNeedle.SetName("CauteryToNeedle")
      slicer.mrmlScene.AddNode(self.CauteryToNeedle)
      
    # Create transforms that will be updated through OpenIGTLink
      
    self.cauteryToReference = slicer.util.getNode('CauteryToReference')
    if not self.cauteryToReference:
      self.cauteryToReference=slicer.vtkMRMLLinearTransformNode()
      self.cauteryToReference.SetName("CauteryToReference")
      slicer.mrmlScene.AddNode(self.cauteryToReference)

    self.needleToReference = slicer.util.getNode('NeedleToReference')
    if not self.needleToReference:
      self.needleToReference=slicer.vtkMRMLLinearTransformNode()
      self.needleToReference.SetName("NeedleToReference")
      slicer.mrmlScene.AddNode(self.needleToReference)
      
    # Cameras
    logging.debug('Create cameras')
      
    self.LeftCamera = slicer.util.getNode('Left Camera')
    if not self.LeftCamera:
      self.LeftCamera=slicer.vtkMRMLCameraNode()
      self.LeftCamera.SetName("Left Camera")
      slicer.mrmlScene.AddNode(self.LeftCamera)

    self.RightCamera = slicer.util.getNode('Right Camera')
    if not self.RightCamera:
      self.RightCamera=slicer.vtkMRMLCameraNode()
      self.RightCamera.SetName("Right Camera")
      slicer.mrmlScene.AddNode(self.RightCamera)
    
    # Models
    logging.debug('Create models')

    self.cauteryModel_CauteryTip = slicer.util.getNode('CauteryModel')
    if not self.cauteryModel_CauteryTip:
      if (self.parameterNode.GetParameter('TestMode')=='True'):
          moduleDirectoryPath = slicer.modules.lumpnav.path.replace('LumpNav.py', '')
          slicer.util.loadModel(qt.QDir.toNativeSeparators(moduleDirectoryPath + '../../../models/temporary/cautery.stl'))
          self.cauteryModel_CauteryTip=slicer.util.getNode(pattern="cautery")
      else:
          slicer.modules.createmodels.logic().CreateNeedle(100,1.0,2.5,0)
          self.cauteryModel_CauteryTip=slicer.util.getNode(pattern="NeedleModel")
          self.cauteryModel_CauteryTip.GetDisplayNode().SetColor(1.0, 1.0, 0)
      self.cauteryModel_CauteryTip.SetName("CauteryModel")

    self.needleModel_NeedleTip = slicer.util.getNode('NeedleModel')
    if not self.needleModel_NeedleTip:
      slicer.modules.createmodels.logic().CreateNeedle(80,1.0,2.5,0)
      self.needleModel_NeedleTip=slicer.util.getNode(pattern="NeedleModel")
      self.needleModel_NeedleTip.GetDisplayNode().SetColor(0.333333, 1.0, 1.0)
      self.needleModel_NeedleTip.SetName("NeedleModel")
      self.needleModel_NeedleTip.GetDisplayNode().SliceIntersectionVisibilityOn()

    # Create surface from point set
    
    logging.debug('Create surface from point set')

    self.tumorModel_Needle = slicer.util.getNode('TumorModel')
    if not self.tumorModel_Needle:
      self.tumorModel_Needle = slicer.vtkMRMLModelNode()
      self.tumorModel_Needle.SetName("TumorModel")
      sphereSource = vtk.vtkSphereSource()
      sphereSource.SetRadius(0.001)
      self.tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())      
      slicer.mrmlScene.AddNode(self.tumorModel_Needle)
      # Add display node
      modelDisplayNode = slicer.vtkMRMLModelDisplayNode()
      modelDisplayNode.SetColor(0,1,0) # Green
      modelDisplayNode.BackfaceCullingOff()
      modelDisplayNode.SliceIntersectionVisibilityOn()
      modelDisplayNode.SetSliceIntersectionThickness(4)
      modelDisplayNode.SetOpacity(0.3) # Between 0-1, 1 being opaque
      slicer.mrmlScene.AddNode(modelDisplayNode)
      self.tumorModel_Needle.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

    tumorMarkups_Needle = slicer.util.getNode('T')
    if not tumorMarkups_Needle:
      tumorMarkups_Needle = slicer.vtkMRMLMarkupsFiducialNode()
      tumorMarkups_Needle.SetName("T")
      slicer.mrmlScene.AddNode(tumorMarkups_Needle)
      tumorMarkups_Needle.CreateDefaultDisplayNodes()
      tumorMarkups_Needle.GetDisplayNode().SetTextScale(0)
    self.setAndObserveTumorMarkupsNode(tumorMarkups_Needle)

    # Set up breach warning node
    logging.debug('Set up breach warning')
    self.breachWarningNode = slicer.util.getNode('LumpNavBreachWarning')

    if not self.breachWarningNode:
      self.breachWarningNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLBreachWarningNode')
      self.breachWarningNode.SetName("LumpNavBreachWarning")
      slicer.mrmlScene.AddNode(self.breachWarningNode)
      self.breachWarningNode.SetPlayWarningSound(True)
      self.breachWarningNode.SetWarningColor(1,0,0)      
      self.breachWarningNode.SetOriginalColor(self.tumorModel_Needle.GetDisplayNode().GetColor())
      self.breachWarningNode.SetAndObserveToolTransformNodeId(self.cauteryTipToCautery.GetID())
      self.breachWarningNode.SetAndObserveWatchedModelNodeID(self.tumorModel_Needle.GetID())
      breachWarningLogic = slicer.modules.breachwarning.logic()
      breachWarningLogic.SetLineToClosestPointVisibility(False, self.breachWarningNode)
      
    # Set up breach warning light
    import BreachWarningLight
    logging.debug('Set up breach warning light')
    self.breachWarningLightLogic = BreachWarningLight.BreachWarningLightLogic()
    self.breachWarningLightLogic.setMarginSizeMm(float(self.parameterNode.GetParameter('BreachWarningLightMarginSizeMm')))
    if (self.parameterNode.GetParameter('EnableBreachWarningLight')=='True'):
      logging.debug("BreachWarningLight: active")
      self.breachWarningLightLogic.startLightFeedback(self.breachWarningNode, self.connectorNode)
    else:
      logging.debug("BreachWarningLight: shutdown")
      self.breachWarningLightLogic.shutdownLight(self.connectorNode)

    # Build transform tree
    logging.debug('Set up transform tree')
    self.cauteryToReference.SetAndObserveTransformNodeID(self.ReferenceToRas.GetID())
    self.cauteryCameraToCautery.SetAndObserveTransformNodeID(self.cauteryToReference.GetID())
    self.cauteryTipToCautery.SetAndObserveTransformNodeID(self.cauteryToReference.GetID())
    self.cauteryModelToCauteryTip.SetAndObserveTransformNodeID(self.cauteryTipToCautery.GetID())
    self.needleToReference.SetAndObserveTransformNodeID(self.ReferenceToRas.GetID())
    self.needleTipToNeedle.SetAndObserveTransformNodeID(self.needleToReference.GetID())
    self.needleBaseToNeedle.SetAndObserveTransformNodeID(self.needleToReference.GetID())
    self.needleModelToNeedleTip.SetAndObserveTransformNodeID(self.needleTipToNeedle.GetID())
    self.cauteryModel_CauteryTip.SetAndObserveTransformNodeID(self.cauteryModelToCauteryTip.GetID())
    self.needleModel_NeedleTip.SetAndObserveTransformNodeID(self.needleModelToNeedleTip.GetID())
    self.tumorModel_Needle.SetAndObserveTransformNodeID(self.needleToReference.GetID())
    self.tumorMarkups_Needle.SetAndObserveTransformNodeID(self.needleToReference.GetID())      
    # self.liveUltrasoundNode_Reference.SetAndObserveTransformNodeID(self.ReferenceToRas.GetID())
    
    # Hide slice view annotations (patient name, scale, color bar, etc.) as they
    # decrease reslicing performance by 20%-100%
    logging.debug('Hide slice view annotations')
    import DataProbe
    dataProbeUtil=DataProbe.DataProbeLib.DataProbeUtil()
    dataProbeParameterNode=dataProbeUtil.getParameterNode()
    dataProbeParameterNode.SetParameter('showSliceViewAnnotations', '0')

  def disconnect(self):#TODO see connect
    logging.debug('LumpNav.disconnect()')
    Guidelet.disconnect(self)
      
    # Remove observer to old parameter node
    if self.tumorMarkups_Needle and self.tumorMarkups_NeedleObserver:
      self.tumorMarkups_Needle.RemoveObserver(self.tumorMarkups_NeedleObserver)
      self.tumorMarkups_NeedleObserver = None

    self.calibrationCollapsibleButton.disconnect('toggled(bool)', self.onCalibrationPanelToggled)
    self.navigationCollapsibleButton.disconnect('toggled(bool)', self.onNavigationPanelToggled)

    self.cauteryPivotButton.disconnect('clicked()', self.onCauteryPivotClicked)
    self.needlePivotButton.disconnect('clicked()', self.onNeedlePivotClicked)
    self.deleteLastFiducialButton.disconnect('clicked()', self.onDeleteLastFiducialClicked)
    self.deleteLastFiducialDuringNavigationButton.disconnect('clicked()', self.onDeleteLastFiducialClicked)    
    self.deleteAllFiducialsButton.disconnect('clicked()', self.onDeleteAllFiducialsClicked)
    self.placeButton.disconnect('clicked(bool)', self.onPlaceClicked)

    self.rightCameraButton.disconnect('clicked()', self.onRightCameraButtonClicked)
    self.leftCameraButton.disconnect('clicked()', self.onLeftCameraButtonClicked)

    self.pivotSamplingTimer.disconnect('timeout()',self.onPivotSamplingTimeout)

    self.cameraViewAngleSlider.disconnect('valueChanged(double)', self.viewpointLogic.SetCameraViewAngleDeg)
    self.cameraXPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.SetCameraXPosMm)
    self.cameraYPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.SetCameraYPosMm)
    self.cameraZPosSlider.disconnect('valueChanged(double)', self.viewpointLogic.SetCameraZPosMm)
    
    self.placeTumorPointAtCauteryTipButton.disconnect('clicked(bool)', self.onPlaceTumorPointAtCauteryTipClicked)

    
  def onPivotSamplingTimeout(self):#lumpnav
    self.countdownLabel.setText("Pivot calibrating for {0:.0f} more seconds".format(self.pivotCalibrationStopTime-time.time())) 
    if(time.time()<self.pivotCalibrationStopTime):
      # continue
      self.pivotSamplingTimer.start()
    else:
      # calibration completed
      self.onStopPivotCalibration()

  def startPivotCalibration(self, toolToReferenceTransformName, toolToReferenceTransformNode, toolTipToToolTransformNode):#lumpnav
    self.needlePivotButton.setEnabled(False)
    self.cauteryPivotButton.setEnabled(False)
    self.pivotCalibrationResultTargetNode =  toolTipToToolTransformNode
    self.pivotCalibrationResultTargetName = toolToReferenceTransformName
    self.pivotCalibrationLogic.SetAndObserveTransformNode( toolToReferenceTransformNode );
    self.pivotCalibrationStopTime=time.time()+float(self.parameterNode.GetParameter('PivotCalibrationDurationSec'))
    self.pivotCalibrationLogic.SetRecordingState(True)
    self.onPivotSamplingTimeout()

  def onStopPivotCalibration(self):#lumpnav
    self.pivotCalibrationLogic.SetRecordingState(False)
    self.needlePivotButton.setEnabled(True)
    self.cauteryPivotButton.setEnabled(True)
    self.pivotCalibrationLogic.ComputePivotCalibration()
    if(self.pivotCalibrationLogic.GetPivotRMSE() >= float(self.parameterNode.GetParameter('PivotCalibrationErrorThresholdMm'))):
        self.countdownLabel.setText("Calibration failed, error = %f mm, please calibrate again!"  % self.pivotCalibrationLogic.GetPivotRMSE())
        self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
        return
    tooltipToToolMatrix = vtk.vtkMatrix4x4()
    self.pivotCalibrationLogic.GetToolTipToToolMatrix(tooltipToToolMatrix)
    self.pivotCalibrationLogic.ClearToolToReferenceMatrices()
    self.pivotCalibrationResultTargetNode.SetMatrixTransformToParent(tooltipToToolMatrix)
    self.logic.writeTransformToSettings(self.pivotCalibrationResultTargetName, tooltipToToolMatrix, self.configurationName)
    self.countdownLabel.setText("Calibration completed, error = %f mm" % self.pivotCalibrationLogic.GetPivotRMSE())
    logging.debug("Pivot calibration completed. Tool: {0}. RMSE = {1} mm".format(self.pivotCalibrationResultTargetNode.GetName(), self.pivotCalibrationLogic.GetPivotRMSE()))
    # We compute approximate needle length if we perform pivot calibration for the needle
    if self.pivotCalibrationResultTargetName == 'NeedleTipToNeedle':
      self.updateDisplayedNeedleLength()

  def onCauteryPivotClicked(self):#lumpnav
    logging.debug('onCauteryPivotClicked')
    self.startPivotCalibration('CauteryTipToCautery', self.CauteryToNeedle, self.cauteryTipToCautery)

  def onNeedlePivotClicked(self):#lumpnav
    # NeedleTipToNeedle transform can be computed in two ways:
    # A. Pivot calibration: NeedleTipToNeedle is computed by pivot calibration;
    #    needle length is computed from difference of NeedleTipToNeedle and NeedleBaseToNeedle transform
    # B. Needle length specification: NeedleTipToNeedle is computed by offsetting NeedleBaseToNeedle by the
    #    needle length the user specifies.
    # (NeedleBaseToNeedle is constant, depends on the geometry of the needle clip)
    logging.debug('onNeedlePivotClicked')
    self.startPivotCalibration('NeedleTipToNeedle', self.needleToReference, self.needleTipToNeedle)

  def onPlaceClicked(self, pushed):
    logging.debug('onPlaceClicked')
    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
    if pushed:
      # activate placement mode
      selectionNode = slicer.app.applicationLogic().GetSelectionNode()
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
      selectionNode.SetActivePlaceNodeID(self.tumorMarkups_Needle.GetID())
      interactionNode.SetPlaceModePersistence(1)
      interactionNode.SetCurrentInteractionMode(interactionNode.Place)
    else:
      # deactivate placement mode
      interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)

  def onDeleteLastFiducialClicked(self):
    numberOfPoints = self.tumorMarkups_Needle.GetNumberOfFiducials()
    self.tumorMarkups_Needle.RemoveMarkup(numberOfPoints-1)
    if numberOfPoints<=1:
        self.deleteLastFiducialButton.setEnabled(False)
        self.deleteAllFiducialsButton.setEnabled(False)
        self.deleteLastFiducialDuringNavigationButton.setEnabled(False)

  def onDeleteAllFiducialsClicked(self):
    self.tumorMarkups_Needle.RemoveAllMarkups()
    self.deleteLastFiducialButton.setEnabled(False)
    self.deleteAllFiducialsButton.setEnabled(False)
    self.deleteLastFiducialDuringNavigationButton.setEnabled(False)
    sphereSource = vtk.vtkSphereSource()
    sphereSource.SetRadius(0.001)
    self.tumorModel_Needle.SetPolyDataConnection(sphereSource.GetOutputPort())      
    self.tumorModel_Needle.Modified()

  def onPlaceTumorPointAtCauteryTipClicked(self):
    cauteryTipToNeedle = vtk.vtkMatrix4x4()
    self.cauteryTipToCautery.GetMatrixTransformToNode(self.needleToReference, cauteryTipToNeedle)
    self.tumorMarkups_Needle.AddFiducial(cauteryTipToNeedle.GetElement(0,3), cauteryTipToNeedle.GetElement(1,3), cauteryTipToNeedle.GetElement(2,3))
      
  def setupCalibrationPanel(self):
    logging.debug('setupCalibrationPanel')

    self.calibrationCollapsibleButton.setProperty('collapsedHeight', 20)
    self.calibrationCollapsibleButton.text = 'Tool calibration'
    self.sliceletPanelLayout.addWidget(self.calibrationCollapsibleButton)

    self.calibrationLayout = qt.QFormLayout(self.calibrationCollapsibleButton)
    self.calibrationLayout.setContentsMargins(12, 4, 4, 4)
    self.calibrationLayout.setSpacing(4)

    self.cauteryPivotButton = qt.QPushButton('Start cautery calibration')
    self.calibrationLayout.addRow(self.cauteryPivotButton)

    self.needleLengthLayout = qt.QFormLayout(self.calibrationCollapsibleButton)
    self.needleLengthSpinBox = qt.QSpinBox()
    self.needleLengthSpinBox.setMinimum(10)
    self.needleLengthSpinBox.setMaximum(200)
    self.needleLengthLayout.addRow('Needle length (mm)', self.needleLengthSpinBox)
    self.calibrationLayout.addRow(self.needleLengthLayout)
    
    # "Advanced needle calibration" Collapsible
    self.advancedNeedleCalibrationCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.advancedNeedleCalibrationCollapsibleButton.title = "Advanced needle calibration"
    self.advancedNeedleCalibrationCollapsibleButton.collapsed=True
    self.calibrationLayout.addRow(self.advancedNeedleCalibrationCollapsibleButton)

    # Layout within the collapsible button
    self.advancedNeedleCalibrationFormLayout = qt.QFormLayout(self.advancedNeedleCalibrationCollapsibleButton)
    
    self.needlePivotButton = qt.QPushButton('Start needle calibration')
    self.advancedNeedleCalibrationFormLayout.addRow(self.needlePivotButton)

    self.countdownLabel = qt.QLabel()
    self.calibrationLayout.addRow(self.countdownLabel)
    
    self.pivotSamplingTimer = qt.QTimer()
    self.pivotSamplingTimer.setInterval(500)
    self.pivotSamplingTimer.setSingleShot(True)

  def addTumorContouringToUltrasoundPanel(self):

    self.ultrasoundCollapsibleButton.text = "Tumor contouring"

    self.placeButton = qt.QPushButton("Mark points")
    self.placeButton.setCheckable(True)
    self.placeButton.setIcon(qt.QIcon(":/Icons/MarkupsMouseModePlace.png"))
    self.ultrasoundLayout.addRow(self.placeButton)

    self.deleteLastFiducialButton = qt.QPushButton("Delete last")
    self.deleteLastFiducialButton.setIcon(qt.QIcon(":/Icons/MarkupsDelete.png"))
    self.deleteLastFiducialButton.setEnabled(False)

    self.deleteAllFiducialsButton = qt.QPushButton("Delete all")
    self.deleteAllFiducialsButton.setIcon(qt.QIcon(":/Icons/MarkupsDeleteAllRows.png"))
    self.deleteAllFiducialsButton.setEnabled(False)

    hbox = qt.QHBoxLayout()
    hbox.addWidget(self.deleteLastFiducialButton)
    hbox.addWidget(self.deleteAllFiducialsButton)
    self.ultrasoundLayout.addRow(hbox)

  def setupNavigationPanel(self):
    logging.debug('setupNavigationPanel')

    self.sliderTranslationDefaultMm = 0
    self.sliderTranslationMinMm     = -500
    self.sliderTranslationMaxMm     = 500
    self.sliderViewAngleDefaultDeg  = 30
    self.cameraViewAngleMinDeg      = 5.0  # maximum magnification
    self.cameraViewAngleMaxDeg      = 150.0 # minimum magnification
    
    self.sliderSingleStepValue = 1
    self.sliderPageStepValue   = 10

    self.navigationCollapsibleButton.setProperty('collapsedHeight', 20)
    self.navigationCollapsibleButton.text = "Navigation"
    self.sliceletPanelLayout.addWidget(self.navigationCollapsibleButton)

    self.navigationCollapsibleLayout = qt.QFormLayout(self.navigationCollapsibleButton)
    self.navigationCollapsibleLayout.setContentsMargins(12, 4, 4, 4)
    self.navigationCollapsibleLayout.setSpacing(4)

    self.rightCameraButton = qt.QPushButton("Setup right camera")
    self.rightCameraButton.setCheckable(True)

    self.leftCameraButton = qt.QPushButton("Setup left camera")
    self.leftCameraButton.setCheckable(True)

    hbox = qt.QHBoxLayout()
    hbox.addWidget(self.leftCameraButton)
    hbox.addWidget(self.rightCameraButton)
    self.navigationCollapsibleLayout.addRow(hbox)

    # "Camera Control" Collapsible
    self.zoomCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.zoomCollapsibleButton.collapsed=True
    self.zoomCollapsibleButton.title = "Zoom"
    self.navigationCollapsibleLayout.addRow(self.zoomCollapsibleButton)

    # Layout within the collapsible button
    self.zoomFormLayout = qt.QFormLayout(self.zoomCollapsibleButton)
    
    # Camera distance to focal point slider
    self.cameraViewAngleLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraViewAngleLabel.setText("Field of view [degrees]: ")
    self.cameraViewAngleSlider = slicer.qMRMLSliderWidget()
    self.cameraViewAngleSlider.minimum = self.cameraViewAngleMinDeg
    self.cameraViewAngleSlider.maximum = self.cameraViewAngleMaxDeg
    self.cameraViewAngleSlider.value = self.sliderViewAngleDefaultDeg
    self.cameraViewAngleSlider.singleStep = self.sliderSingleStepValue
    self.cameraViewAngleSlider.pageStep = self.sliderPageStepValue
    self.cameraViewAngleSlider.setDisabled(True)
    self.zoomFormLayout.addRow(self.cameraViewAngleLabel,self.cameraViewAngleSlider)
    
    # "Camera Control" Collapsible
    self.translationCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.translationCollapsibleButton.title = "Translation"
    self.translationCollapsibleButton.collapsed=True
    self.navigationCollapsibleLayout.addRow(self.translationCollapsibleButton)

    # Layout within the collapsible button
    self.translationFormLayout = qt.QFormLayout(self.translationCollapsibleButton)        

    self.cameraXPosLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraXPosLabel.text = "Left/Right [mm]: "
    self.cameraXPosSlider = slicer.qMRMLSliderWidget()
    self.cameraXPosSlider.minimum = self.sliderTranslationMinMm
    self.cameraXPosSlider.maximum = self.sliderTranslationMaxMm
    self.cameraXPosSlider.value = self.sliderTranslationDefaultMm
    self.cameraXPosSlider.singleStep = self.sliderSingleStepValue
    self.cameraXPosSlider.pageStep = self.sliderPageStepValue
    self.cameraXPosSlider.setDisabled(True)
    self.translationFormLayout.addRow(self.cameraXPosLabel,self.cameraXPosSlider)
    
    self.cameraYPosLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraYPosLabel.setText("Down/Up [mm]: ")
    self.cameraYPosSlider = slicer.qMRMLSliderWidget()
    self.cameraYPosSlider.minimum = self.sliderTranslationMinMm
    self.cameraYPosSlider.maximum = self.sliderTranslationMaxMm
    self.cameraYPosSlider.value = self.sliderTranslationDefaultMm
    self.cameraYPosSlider.singleStep = self.sliderSingleStepValue
    self.cameraYPosSlider.pageStep = self.sliderPageStepValue
    self.cameraYPosSlider.setDisabled(True)
    self.translationFormLayout.addRow(self.cameraYPosLabel,self.cameraYPosSlider)
    
    self.cameraZPosLabel = qt.QLabel(qt.Qt.Horizontal,None)
    self.cameraZPosLabel.setText("Front/Back [mm]: ")
    self.cameraZPosSlider = slicer.qMRMLSliderWidget()
    self.cameraZPosSlider.minimum = self.sliderTranslationMinMm
    self.cameraZPosSlider.maximum = self.sliderTranslationMaxMm
    self.cameraZPosSlider.value = self.sliderTranslationDefaultMm
    self.cameraZPosSlider.singleStep = self.sliderSingleStepValue
    self.cameraZPosSlider.pageStep = self.sliderPageStepValue
    self.cameraZPosSlider.setDisabled(True)
    self.translationFormLayout.addRow(self.cameraZPosLabel,self.cameraZPosSlider)

    # "Contour adjustment" Collapsible
    self.contourAdjustmentCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    self.contourAdjustmentCollapsibleButton.title = "Contour adjustment"
    self.contourAdjustmentCollapsibleButton.collapsed=True
    self.navigationCollapsibleLayout.addRow(self.contourAdjustmentCollapsibleButton)

    # Layout within the collapsible button
    self.contourAdjustmentFormLayout = qt.QFormLayout(self.contourAdjustmentCollapsibleButton)

    self.placeTumorPointAtCauteryTipButton = qt.QPushButton("Mark point at cautery tip")
    self.contourAdjustmentFormLayout.addRow(self.placeTumorPointAtCauteryTipButton)
    
    self.deleteLastFiducialDuringNavigationButton = qt.QPushButton("Delete last")
    self.deleteLastFiducialDuringNavigationButton.setIcon(qt.QIcon(":/Icons/MarkupsDelete.png"))
    self.deleteLastFiducialDuringNavigationButton.setEnabled(False)
    self.contourAdjustmentFormLayout.addRow(self.deleteLastFiducialDuringNavigationButton)

  def onCalibrationPanelToggled(self, toggled):
    if toggled == False:
      return

    logging.debug('onCalibrationPanelToggled: {0}'.format(toggled))
    
    if self.tumorMarkups_Needle:
      self.tumorMarkups_Needle.SetDisplayVisibility(0)

    self.selectView(self.VIEW_ULTRASOUND_3D) 

  def onUltrasoundPanelToggled(self, toggled):
    Guidelet.onUltrasoundPanelToggled(self, toggled)
    
    if self.tumorMarkups_Needle:
        self.tumorMarkups_Needle.SetDisplayVisibility(0)
  
  def createTumorFromMarkups(self):
    logging.debug('createTumorFromMarkups')
    #self.tumorMarkups_Needle.SetDisplayVisibility(0)
    
    # Create polydata point set from markup points
    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()
    
    numberOfPoints = self.tumorMarkups_Needle.GetNumberOfFiducials()

    if numberOfPoints>0:
        self.deleteLastFiducialButton.setEnabled(True)
        self.deleteAllFiducialsButton.setEnabled(True)
        self.deleteLastFiducialDuringNavigationButton.setEnabled(True)
    
    # Surface generation algorithms behave unpredictably when there are not enough points
    # return if there are very few points
    if numberOfPoints<1:
      return

    points.SetNumberOfPoints(numberOfPoints)
    new_coord = [0.0, 0.0, 0.0]

    for i in range(numberOfPoints):
      self.tumorMarkups_Needle.GetNthFiducialPosition(i,new_coord)
      points.SetPoint(i, new_coord)

    cellArray.InsertNextCell(numberOfPoints)
    for i in range(numberOfPoints):
      cellArray.InsertCellPoint(i)

    pointPolyData = vtk.vtkPolyData()
    pointPolyData.SetLines(cellArray)
    pointPolyData.SetPoints(points)
    
    delaunay = vtk.vtkDelaunay3D()

    if numberOfPoints<10:
      logging.debug("use glyphs")
      sphere = vtk.vtkCubeSource()
      glyph = vtk.vtkGlyph3D()
      glyph.SetInputData(pointPolyData)
      glyph.SetSourceConnection(sphere.GetOutputPort())
      #glyph.SetVectorModeToUseNormal()
      #glyph.SetScaleModeToScaleByVector()
      #glyph.SetScaleFactor(0.25)
      delaunay.SetInputConnection(glyph.GetOutputPort())
    else:
      delaunay.SetInputData(pointPolyData)

    surfaceFilter = vtk.vtkDataSetSurfaceFilter()
    surfaceFilter.SetInputConnection(delaunay.GetOutputPort())

    smoother = vtk.vtkButterflySubdivisionFilter()
    smoother.SetInputConnection(surfaceFilter.GetOutputPort())
    smoother.SetNumberOfSubdivisions(3)
    smoother.Update()
    
    forceConvexShape = True

    if (forceConvexShape == True):
        delaunaySmooth = vtk.vtkDelaunay3D()
        delaunaySmooth.SetInputData(smoother.GetOutput())
        delaunaySmooth.Update()
    
        smoothSurfaceFilter = vtk.vtkDataSetSurfaceFilter()
        smoothSurfaceFilter.SetInputConnection(delaunaySmooth.GetOutputPort())
        self.tumorModel_Needle.SetPolyDataConnection(smoothSurfaceFilter.GetOutputPort())
    else:
        self.tumorModel_Needle.SetPolyDataConnection(smoother.GetOutputPort())
    
    self.tumorModel_Needle.Modified()

  def setupViewpoint(self):
    rightView = slicer.util.getNode("View2")
    self.RightCamera.SetActiveTag(rightView.GetID())
    leftView = slicer.util.getNode("View1")
    self.LeftCamera.SetActiveTag(leftView.GetID())

  def setDisableSliders(self, disable):
    self.cameraViewAngleSlider.setDisabled(disable)
    self.cameraXPosSlider.setDisabled(disable)
    self.cameraZPosSlider.setDisabled(disable)
    self.cameraYPosSlider.setDisabled(disable)

  def onRightCameraButtonClicked(self):
    logging.debug("onRightCameraButtonClicked {0}".format(self.rightCameraButton.isChecked()))
    if (self.rightCameraButton.isChecked()== True):
        self.leftCameraButton.setDisabled(True)
        self.viewpointLogic.setCameraNode(self.RightCamera)
        self.viewpointLogic.setTransformNode(self.cauteryCameraToCautery)
        self.viewpointLogic.startViewpoint()
        self.setDisableSliders(False)
    else:
        self.setDisableSliders(True)
        self.viewpointLogic.stopViewpoint()
        self.leftCameraButton.setDisabled(False)

  def onLeftCameraButtonClicked(self):
    logging.debug("onLeftCameraButtonClicked {0}".format(self.leftCameraButton.isChecked()))
    if (self.leftCameraButton.isChecked() == True):
      self.viewpointLogic.setCameraNode(self.LeftCamera)
      self.viewpointLogic.setTransformNode(self.cauteryCameraToCautery)
      self.viewpointLogic.startViewpoint()
      self.rightCameraButton.setDisabled(True)
      self.setDisableSliders(False)
    else:
      self.setDisableSliders(True)
      self.viewpointLogic.stopViewpoint()
      self.rightCameraButton.setDisabled(False)

  def onNavigationPanelToggled(self, toggled):
  
    breachWarningLogic = slicer.modules.breachwarning.logic()
    showTrajectoryToClosestPoint = toggled and (self.parameterNode.GetParameter('TipToSurfaceDistanceTrajectory')=='True')
    breachWarningLogic.SetLineToClosestPointVisibility(showTrajectoryToClosestPoint, self.breachWarningNode)
    if showTrajectoryToClosestPoint:
      breachWarningLogic.SetLineToClosestPointTextScale(float(self.parameterNode.GetParameter('TipToSurfaceDistanceTextScale')), self.breachWarningNode)
      breachWarningLogic.SetLineToClosestPointColor(0,0,1, self.breachWarningNode)
  
    if toggled == False:
      return

    logging.debug('onNavigationPanelToggled')
    self.selectView(self.VIEW_DUAL_3D)
    if self.tumorMarkups_Needle:
      self.tumorMarkups_Needle.SetDisplayVisibility(0)
    self.setupViewpoint()

    ## Stop live ultrasound.
    #if self.connectorNode != None:
    #  self.connectorNode.Stop()

  def onTumorMarkupsNodeModified(self, observer, eventid):
    self.createTumorFromMarkups()

  def setAndObserveTumorMarkupsNode(self, tumorMarkups_Needle):
    if tumorMarkups_Needle == self.tumorMarkups_Needle and self.tumorMarkups_NeedleObserver:
      # no change and node is already observed
      return
    # Remove observer to old parameter node
    if self.tumorMarkups_Needle and self.tumorMarkups_NeedleObserver:
      self.tumorMarkups_Needle.RemoveObserver(self.tumorMarkups_NeedleObserver)
      self.tumorMarkups_NeedleObserver = None
    # Set and observe new parameter node
    self.tumorMarkups_Needle = tumorMarkups_Needle
    if self.tumorMarkups_Needle:
      self.tumorMarkups_NeedleObserver = self.tumorMarkups_Needle.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onTumorMarkupsNodeModified)
      
  def onNeedleLengthModified(self, newLength):
    logging.debug('onNeedleLengthModified {0}'.format(newLength))
    needleBaseToNeedleMatrix = self.needleBaseToNeedle.GetMatrixTransformToParent()
    # NeedleTip and NeedleBase coordinate system have the same axes, just the origin is different (tip/base of the needle)
    needleTipToNeedleBaseMatrix = vtk.vtkMatrix4x4()
    needleTipToNeedleBaseMatrix.SetElement(1,3,newLength)
    needleTipToNeedleMatrix = vtk.vtkMatrix4x4()
    # needleBaseToNeedleMatrix * needleTipToNeedleBaseMatrix = needleTipToNeedleMatrix
    vtk.vtkMatrix4x4.Multiply4x4(needleBaseToNeedleMatrix, needleTipToNeedleBaseMatrix, needleTipToNeedleMatrix)
    self.needleTipToNeedle.SetMatrixTransformToParent(needleTipToNeedleMatrix)
    self.logic.writeTransformToSettings('NeedleTipToNeedle', needleTipToNeedleMatrix, self.configurationName)

  def updateDisplayedNeedleLength(self):
    needleTipToNeedleBaseTransform = vtk.vtkMatrix4x4()
    self.needleTipToNeedle.GetMatrixTransformToNode(self.needleBaseToNeedle, needleTipToNeedleBaseTransform)
    needleLength = math.sqrt(needleTipToNeedleBaseTransform.GetElement(0,3)**2+needleTipToNeedleBaseTransform.GetElement(1,3)**2+needleTipToNeedleBaseTransform.GetElement(2,3)**2)
    wasBlocked = self.needleLengthSpinBox.blockSignals(True)
    self.needleLengthSpinBox.setValue(needleLength)
    self.needleLengthSpinBox.blockSignals(wasBlocked)

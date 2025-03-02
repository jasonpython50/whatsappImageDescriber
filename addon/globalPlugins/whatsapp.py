# globalPlugins/whatsappImageDescriber/__init__.py
import os
import tempfile
import base64
import json
import threading
import globalPluginHandler
import api
import ui
import scriptHandler
from scriptHandler import script
import wx
import config
from logHandler import log
import controlTypes
import speech
import mouseHandler
import winUser
import requests
import io
import time
import gui
from gui import settingsDialogs, guiHelper

# Configuration specification with separate API keys for each service
SPEC = {
    'openaiApiKey': 'string(default="")',
    'geminiApiKey': 'string(default="")',
    'claudeApiKey': 'string(default="")',
    'apiService': 'string(default="openai")',  # Options: openai, gemini, claude
    'selectedModel': 'string(default="")',
    'maxTokens': 'integer(default=300)',
    'language': 'string(default="English")'
}

# Model options by service
MODEL_OPTIONS = {
    "openai": ["gpt-4-vision-preview", "gpt-4o"],
    "gemini": ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"],
    "claude": ["claude-3-7-sonnet-20250219", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
}

# Text Window Class
class TextWindow(wx.Frame):
    """A simple text window to display image descriptions."""

    def __init__(self, text, title, readOnly=True, insertionPoint=0):
        super(TextWindow, self).__init__(wx.GetApp().TopWindow, title=title)
        sizer = wx.BoxSizer(wx.VERTICAL)
        style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH
        self.outputCtrl = wx.TextCtrl(self, style=style)
        self.outputCtrl.Bind(wx.EVT_KEY_DOWN, self.onOutputKeyDown)
        sizer.Add(self.outputCtrl, proportion=1, flag=wx.EXPAND)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.outputCtrl.SetValue(text)
        self.outputCtrl.SetFocus()
        self.outputCtrl.SetInsertionPoint(insertionPoint)
        self.Raise()
        self.Maximize()
        self.Show()

    def onOutputKeyDown(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
        event.Skip()

# Settings Panel
class WhatsAppImageDescriptionSettingsPanel(settingsDialogs.SettingsPanel):
    title = "WhatsApp Image Description"
    
    def makeSettings(self, sizer):
        helper = guiHelper.BoxSizerHelper(self, sizer=sizer)
        
        # API Service
        apiServiceChoices = [
            "OpenAI (GPT-4 Vision)",
            "Google Gemini",
            "Anthropic Claude"
        ]
        self.apiServiceChoice = helper.addLabeledControl(
            "AI Service:",
            wx.Choice,
            choices=apiServiceChoices
        )
        
        # Set the current selection
        apiService = config.conf["WhatsAppImageDescription"]["apiService"]
        if apiService == "openai":
            self.apiServiceChoice.SetSelection(0)
        elif apiService == "gemini":
            self.apiServiceChoice.SetSelection(1)
        elif apiService == "claude":
            self.apiServiceChoice.SetSelection(2)
        else:
            self.apiServiceChoice.SetSelection(0)
            
        # Bind the event to update API key field and model choices when service changes
        self.apiServiceChoice.Bind(wx.EVT_CHOICE, self.onApiServiceChange)
        
        # All API Key fields
        self.openaiApiKeyEdit = helper.addLabeledControl(
            "OpenAI API Key:",
            wx.TextCtrl,
            value=config.conf["WhatsAppImageDescription"]["openaiApiKey"],
            style=wx.TE_PASSWORD
        )
        
        self.geminiApiKeyEdit = helper.addLabeledControl(
            "Google Gemini API Key:",
            wx.TextCtrl,
            value=config.conf["WhatsAppImageDescription"]["geminiApiKey"],
            style=wx.TE_PASSWORD
        )
        
        self.claudeApiKeyEdit = helper.addLabeledControl(
            "Anthropic Claude API Key:",
            wx.TextCtrl,
            value=config.conf["WhatsAppImageDescription"]["claudeApiKey"],
            style=wx.TE_PASSWORD
        )
        
        # Initially show only the relevant API key field
        self.updateApiKeyVisibility()
        
        # Model Selection
        self.modelChoices = []
        self.updateModelChoices()
        
        self.modelChoice = helper.addLabeledControl(
            "Model:",
            wx.Choice,
            choices=self.modelChoices
        )
        
        # Set current model selection
        self.updateModelSelection()
        
        # Max tokens
        self.maxTokensEdit = helper.addLabeledControl(
            "Maximum response length (tokens):",
            wx.SpinCtrl,
            min=100,
            max=1000,
            initial=config.conf["WhatsAppImageDescription"]["maxTokens"]
        )
        
        # Language
        languageChoices = [
            "English",
            "Spanish",
            "French",
            "German",
            "Italian",
            "Portuguese",
            "Russian",
            "Japanese",
            "Chinese",
            "Arabic"
        ]
        self.languageChoice = helper.addLabeledControl(
            "Description language:",
            wx.Choice,
            choices=languageChoices
        )
        
        # Set the current selection for language
        currentLang = config.conf["WhatsAppImageDescription"]["language"]
        try:
            index = languageChoices.index(currentLang)
            self.languageChoice.SetSelection(index)
        except ValueError:
            self.languageChoice.SetSelection(0)
    
    def updateApiKeyVisibility(self):
        """Show only the relevant API key field based on the selected service."""
        apiServiceIndex = self.apiServiceChoice.GetSelection()
        
        # Hide all API key fields first
        self.openaiApiKeyEdit.Show(False)
        self.geminiApiKeyEdit.Show(False)
        self.claudeApiKeyEdit.Show(False)
        
        # Show only the relevant API key field
        if apiServiceIndex == 0:  # OpenAI
            self.openaiApiKeyEdit.Show(True)
        elif apiServiceIndex == 1:  # Gemini
            self.geminiApiKeyEdit.Show(True)
        elif apiServiceIndex == 2:  # Claude
            self.claudeApiKeyEdit.Show(True)
        
        # Refresh the layout
        self.Layout()
    
    def updateModelChoices(self):
        """Update the model choices based on the selected API service."""
        self.modelChoices.clear()
        
        apiServiceIndex = self.apiServiceChoice.GetSelection()
        if apiServiceIndex == 0:  # OpenAI
            self.modelChoices.extend(MODEL_OPTIONS["openai"])
        elif apiServiceIndex == 1:  # Gemini
            self.modelChoices.extend(MODEL_OPTIONS["gemini"])
        elif apiServiceIndex == 2:  # Claude
            self.modelChoices.extend(MODEL_OPTIONS["claude"])
        
        # Update the choice control if it exists
        if hasattr(self, 'modelChoice'):
            self.modelChoice.Clear()
            self.modelChoice.AppendItems(self.modelChoices)
            self.updateModelSelection()
    
    def updateModelSelection(self):
        """Update the selected model in the choice control."""
        selectedModel = config.conf["WhatsAppImageDescription"]["selectedModel"]
        
        # If no model is selected or the selected model is not in the list
        if not selectedModel or selectedModel not in self.modelChoices:
            # Select the first model if available
            if self.modelChoices:
                self.modelChoice.SetSelection(0)
                return
        
        # Otherwise, select the model that matches the configured one
        for i, model in enumerate(self.modelChoices):
            if model == selectedModel:
                self.modelChoice.SetSelection(i)
                break
    
    def onApiServiceChange(self, evt):
        """Handle API service change by updating model choices and API key field."""
        self.updateApiKeyVisibility()
        self.updateModelChoices()
    
    def onSave(self):
        """Save the settings."""
        # Save API keys
        config.conf["WhatsAppImageDescription"]["openaiApiKey"] = self.openaiApiKeyEdit.GetValue()
        config.conf["WhatsAppImageDescription"]["geminiApiKey"] = self.geminiApiKeyEdit.GetValue()
        config.conf["WhatsAppImageDescription"]["claudeApiKey"] = self.claudeApiKeyEdit.GetValue()
        
        # Save API service selection
        serviceIndex = self.apiServiceChoice.GetSelection()
        if serviceIndex == 0:
            config.conf["WhatsAppImageDescription"]["apiService"] = "openai"
        elif serviceIndex == 1:
            config.conf["WhatsAppImageDescription"]["apiService"] = "gemini"
        elif serviceIndex == 2:
            config.conf["WhatsAppImageDescription"]["apiService"] = "claude"
        
        # Save selected model
        modelIndex = self.modelChoice.GetSelection()
        if 0 <= modelIndex < len(self.modelChoices):
            config.conf["WhatsAppImageDescription"]["selectedModel"] = self.modelChoices[modelIndex]
        
        # Save max tokens
        config.conf["WhatsAppImageDescription"]["maxTokens"] = self.maxTokensEdit.GetValue()
        
        # Save language
        langIndex = self.languageChoice.GetSelection()
        languages = ["English", "Spanish", "French", "German", "Italian", 
                    "Portuguese", "Russian", "Japanese", "Chinese", "Arabic"]
        if 0 <= langIndex < len(languages):
            config.conf["WhatsAppImageDescription"]["language"] = languages[langIndex]

def capture_wx_screenshot(left, top, width, height):
    """Capture a screenshot using wxPython's screen capture functionality."""
    try:
        # Create a wx screen DC
        screen_dc = wx.ScreenDC()
        
        # Create a bitmap to store the screenshot
        screenshot = wx.Bitmap(width, height)
        
        # Create a memory DC to draw on the bitmap
        mem_dc = wx.MemoryDC()
        mem_dc.SelectObject(screenshot)
        
        # Blit the screen DC to the memory DC (copy the screen area to the bitmap)
        mem_dc.Blit(0, 0, width, height, screen_dc, left, top)
        mem_dc.SelectObject(wx.NullBitmap)
        
        # Convert to PNG data
        image = screenshot.ConvertToImage()
        
        # Create a memory stream to save the PNG
        stream = io.BytesIO()
        image.SaveFile(stream, wx.BITMAP_TYPE_PNG)
        stream.seek(0)
        
        # Return the PNG data
        return stream.read()
        
    except Exception as e:
        log.error(f"Error capturing screenshot with wx: {e}")
        return None

def is_whatsapp_window():
    """Check if the current window is WhatsApp (handles both desktop and Store versions)."""
    try:
        foreground = api.getForegroundObject()
        app = foreground.appModule
        
        # Log detailed information for debugging
        app_name = app.appName if app and hasattr(app, 'appName') else "unknown"
        window_title = foreground.name if hasattr(foreground, 'name') else "unknown"
        log.info(f"Current application: {app_name}, Window title: {window_title}")
        
        # Standard WhatsApp desktop check
        if app and hasattr(app, 'appName') and 'whatsapp' in app.appName.lower():
            log.info("Detected standard WhatsApp desktop app")
            return True
            
        # Microsoft Store app check - ApplicationFrameHost with WhatsApp in the title
        if app and hasattr(app, 'appName') and app.appName.lower() == 'applicationframehost':
            if hasattr(foreground, 'name') and 'whatsapp' in foreground.name.lower():
                log.info("Detected Microsoft Store WhatsApp app")
                return True
            
            # Additional check for specific UI elements that might indicate WhatsApp
            # Check for common WhatsApp controls
            for child in foreground.children:
                if hasattr(child, 'name') and 'whatsapp' in child.name.lower():
                    log.info("Found WhatsApp indicator in ApplicationFrameHost window")
                    return True
        
        log.info(f"Not identified as WhatsApp window")
        return False
    except Exception as e:
        log.error(f"Error checking for WhatsApp window: {e}")
        return False

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "WhatsApp Image Description"
    
    def __init__(self):
        super(GlobalPlugin, self).__init__()
        # Initialize the configuration
        config.conf.spec['WhatsAppImageDescription'] = SPEC
        
        # Set default model if not already set
        if not config.conf['WhatsAppImageDescription']['selectedModel']:
            service = config.conf['WhatsAppImageDescription']['apiService']
            if service in MODEL_OPTIONS and MODEL_OPTIONS[service]:
                config.conf['WhatsAppImageDescription']['selectedModel'] = MODEL_OPTIONS[service][0]
        
        # Add settings panel
        settingsDialogs.NVDASettingsDialog.categoryClasses.append(WhatsAppImageDescriptionSettingsPanel)
    
    def terminate(self):
        try:
            settingsDialogs.NVDASettingsDialog.categoryClasses.remove(WhatsAppImageDescriptionSettingsPanel)
        except ValueError:
            pass
        super(GlobalPlugin, self).terminate()
    
    @script(description="Describe the image in the current WhatsApp message", gesture="kb:ALT+I")
    def script_describeImage(self, gesture):
        # Check if we're in WhatsApp (supports both regular and Store versions)
        if not is_whatsapp_window():
            ui.message("This command only works in WhatsApp")
            return
            
        # Check if we're on a message that contains an image
        obj = api.getFocusObject()
        
        # For debugging
        log.info(f"Current focus object: {obj.name}, ID: {obj.UIAAutomationId}")
        
        if obj.UIAAutomationId != "BubbleListItem":
            ui.message("Please navigate to a message first")
            return
        
        # Check if this message contains an image
        imageElement = self._findImageInMessage(obj)
        
        if not imageElement:
            ui.message("No image found in this message")
            return
        
        ui.message("Analyzing image, please wait...")
        
        # Capture the image with extra inspection
        try:
            # Let's check the position of what we're trying to capture
            if not imageElement.location or not imageElement.location.width or not imageElement.location.height:
                ui.message("Cannot determine image location")
                return
                
            left = imageElement.location.left
            top = imageElement.location.top
            width = imageElement.location.width
            height = imageElement.location.height
            
            log.info(f"Image element position: left={left}, top={top}, width={width}, height={height}")
            
            if width < 10 or height < 10:
                ui.message("Image area too small, trying to find the actual image")
                # Try to get the parent message which may have better coordinates
                messageObj = obj
                left = messageObj.location.left
                top = messageObj.location.top
                width = messageObj.location.width
                height = messageObj.location.height
                log.info(f"Using message bounds instead: left={left}, top={top}, width={width}, height={height}")
            
            # Ensure we have a reasonable capture area
            if width > 50 and height > 50:
                # Try moving the mouse over the image to ensure it's visible/activated
                try:
                    p = winUser.POINT(left + width // 2, top + height // 2)
                    winUser.setCursorPos(p.x, p.y)
                    time.sleep(0.2)  # Wait a bit for any hover effects to activate
                except Exception as e:
                    log.error(f"Error moving mouse: {e}")
                
                # Set focus to the image element to ensure it's visible
                imageElement.setFocus()
                time.sleep(0.3)  # Wait a moment for the focus to take effect
                
                # Capture the screen region using wxPython's screenshot capability
                image_data = capture_wx_screenshot(left, top, width, height)
                if not image_data:
                    ui.message("Failed to capture image, trying alternative method")
                    return
                    
                # Send image to AI service in a separate thread to keep NVDA responsive
                threading.Thread(
                    target=self._processImageWithAI, 
                    args=(image_data,)
                ).start()
            else:
                ui.message("Image area too small to capture properly")
                
        except Exception as e:
            log.error(f"Error capturing image: {e}")
            ui.message(f"Error describing image: {str(e)}")
    
    def _findImageInMessage(self, messageObj):
        """Find an image element within a WhatsApp message."""
        try:
            # Log message info for debugging
            log.info(f"Looking for image in message: {messageObj.name}")
            
            # Try to find if this message has direct indicators that it's an image message
            if any(term in messageObj.name.lower() for term in ["image", "photo", "picture", "sent"]):
                log.info(f"Message name suggests it contains an image")
                # We'll try to capture the whole message in this case
                return messageObj
            
            # Look for image elements in the message
            for child in messageObj.children:
                # Check for typical WhatsApp image containers
                if hasattr(child, 'UIAAutomationId') and child.UIAAutomationId in ["ImagePanel", "MediaCard", "MediaContainer"]:
                    log.info(f"Found image container: {child.UIAAutomationId}")
                    return child
                
                # Check for roles associated with images
                if hasattr(child, 'role'):
                    # Log the role for debugging
                    log.info(f"Child role: {child.role}")
                    # Check for common image-related roles
                    try:
                        if child.role == controlTypes.Role.GRAPHIC:
                            return child
                    except:
                        # Fallback for different NVDA versions
                        if hasattr(controlTypes, 'ROLE_GRAPHIC') and child.role == controlTypes.ROLE_GRAPHIC:
                            return child
                    
                # Look for elements that might contain image indicators
                if child.firstChild and hasattr(child.firstChild, 'name'):
                    # WhatsApp sometimes uses icons or specific patterns for images
                    childName = child.firstChild.name
                    log.info(f"First child name: {childName}")
                    if any(term in childName for term in ["\uf40e", "Photo", "image", "picture"]):
                        return child
            
            # If we haven't found an image element by properties, look for visual indicators
            # WhatsApp often wraps images in specific containers
            for child in messageObj.children:
                if hasattr(child, 'childCount') and child.childCount > 0:
                    # Check if this looks like an image container (images often have few children)
                    if child.childCount <= 5 and hasattr(child, 'location'):
                        if child.location.width > 100 and child.location.height > 100:
                            log.info(f"Found potential image container by size")
                            return child
            
            # If we still haven't found anything, return the message itself as a last resort
            log.info(f"No specific image element found, using message as fallback")
            return messageObj
            
        except Exception as e:
            log.error(f"Error finding image element: {e}")
            return messageObj  # Return the message object as a fallback
    
    def _processImageWithAI(self, image_data):
        """Send the image to an AI service and get the description."""
        try:
            apiService = config.conf['WhatsAppImageDescription']['apiService']
            
            # Get the appropriate API key based on the selected service
            if apiService == "openai":
                apiKey = config.conf['WhatsAppImageDescription']['openaiApiKey']
                description = self._describeWithOpenAI(image_data, apiKey)
            elif apiService == "gemini":
                apiKey = config.conf['WhatsAppImageDescription']['geminiApiKey']
                description = self._describeWithGemini(image_data, apiKey)
            elif apiService == "claude":
                apiKey = config.conf['WhatsAppImageDescription']['claudeApiKey']
                description = self._describeWithClaude(image_data, apiKey)
            else:
                description = "Unknown API service selected"
                apiKey = ""
            
            if not apiKey:
                wx.CallAfter(self._showApiKeyDialog)
                return
            
            # Show the description
            if description:
                wx.CallAfter(lambda: TextWindow(
                    description, 
                    "Image Description", 
                    readOnly=True
                ))
            else:
                wx.CallAfter(lambda: ui.message("Could not get image description"))
                
        except Exception as e:
            log.error(f"Error processing image with AI: {e}")
            wx.CallAfter(lambda: ui.message(f"Error getting description: {str(e)}"))
    
    def _describeWithOpenAI(self, image_data, api_key):
        """Use OpenAI's Vision API to describe the image."""
        try:
            if not api_key:
                return "OpenAI API key not configured. Please add your API key in settings."
                
            # Convert image to base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            model = config.conf['WhatsAppImageDescription']['selectedModel']
            if not model or model not in MODEL_OPTIONS["openai"]:
                model = MODEL_OPTIONS["openai"][0]
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Describe this image in detail. If the image contain text, extract the exact text  from the image after a brief description. Use {config.conf['WhatsAppImageDescription']['language']} language."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": config.conf['WhatsAppImageDescription']['maxTokens']
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response_data = response.json()
            
            if 'error' in response_data:
                return f"Error from OpenAI: {response_data['error']['message']}"
            
            return response_data['choices'][0]['message']['content']
            
        except Exception as e:
            log.error(f"OpenAI API error: {e}")
            return f"Error: {str(e)}"
    
    def _describeWithGemini(self, image_data, api_key):
        """Use Google's Gemini API to describe the image."""
        try:
            if not api_key:
                return "Google Gemini API key not configured. Please add your API key in settings."
                
            # Convert image to base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            
            headers = {
                "Content-Type": "application/json"
            }
            
            model_name = config.conf['WhatsAppImageDescription']['selectedModel']
            if not model_name or model_name not in MODEL_OPTIONS["gemini"]:
                model_name = MODEL_OPTIONS["gemini"][0]
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"Describe this image in detail. If the image contain text, extract the exact text  from the image after a brief description. Use {config.conf['WhatsAppImageDescription']['language']} language."
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": encoded_image
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": config.conf['WhatsAppImageDescription']['maxTokens']
                }
            }
            
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={api_key}",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response_data = response.json()
            
            if 'error' in response_data:
                return f"Error from Gemini: {response_data['error']['message']}"
            
            return response_data['candidates'][0]['content']['parts'][0]['text']
            
        except Exception as e:
            log.error(f"Gemini API error: {e}")
            return f"Error: {str(e)}"
    
    def _describeWithClaude(self, image_data, api_key):
        """Use Anthropic's Claude API to describe the image."""
        try:
            if not api_key:
                return "Claude API key not configured. Please add your API key in settings."
                
            # Convert image to base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            model_name = config.conf['WhatsAppImageDescription']['selectedModel']
            if not model_name or model_name not in MODEL_OPTIONS["claude"]:
                model_name = MODEL_OPTIONS["claude"][0]
            
            payload = {
                "model": model_name,
                "max_tokens": config.conf['WhatsAppImageDescription']['maxTokens'],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Describe this image in detail. If the image contain text, extract the exact text  from the image after a brief description. Use {config.conf['WhatsAppImageDescription']['language']} language."
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": encoded_image
                                }
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response_data = response.json()
            
            if 'error' in response_data:
                return f"Error from Claude: {response_data['error']['message']}"
            
            return response_data['content'][0]['text']
            
        except Exception as e:
            log.error(f"Claude API error: {e}")
            return f"Error: {str(e)}"
    
    def _showApiKeyDialog(self):
        """Show a dialog to prompt for API key setup."""
        import gui
        gui.messageBox(
            "To use image description, you need to set up an API key in the WhatsApp Image Description settings.",
            "API Key Required",
            wx.OK | wx.ICON_INFORMATION
        )
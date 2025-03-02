# WhatsApp Image Description

## Overview

WhatsApp Image Description is an NVDA add-on that allows you to get AI-generated descriptions of images in WhatsApp messages. This add-on works with both the desktop version of WhatsApp and the Microsoft Store version.

## Features

* Get detailed descriptions of images in WhatsApp messages
* Support for multiple AI vision services:
  * OpenAI (GPT-4 Vision)
  * Google Gemini 
  * Anthropic Claude
* Customizable response length and description language
* Compatible with both desktop WhatsApp and Microsoft Store version

## Requirements

* NVDA 2024.2 or later
* WhatsApp Desktop (standard version or Microsoft Store version)
* An API key for at least one of the supported AI services:
  * OpenAI API key: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
  * Google Gemini API key: [https://aistudio.google.com/app/apikey](https://ai.google.dev/)
  * Anthropic Claude API key: [https://console.anthropic.com/](https://console.anthropic.com/)
* Gemini offers enough generous rate limiting for free.


## Installation

1. Download the add-on package from the NVDA Add-on Store or the releases page of this repository.
2. Open the add-on package with NVDA, which will launch the installation process.
3. Follow the on-screen instructions to complete the installation.
4. Restart NVDA when prompted.

## Configuration

1. Go to NVDA menu > Preferences > Settings > WhatsApp Image Description.
2. Select your preferred AI service.
3. Enter your API key for the selected service.
4. Choose your preferred AI model.
5. Adjust the maximum response length (in tokens) if needed.
6. Select your preferred description language.
7. Click OK to save your settings.

## Usage

1. Open WhatsApp and navigate to a chat.
2. Navigate to a message containing an image.
3. Press ALT+I to get a description of the image.
4. The description will be displayed in a readable window where you can review it at your own pace.
5. Press ESC to close the description window when finished.

## Troubleshooting

* **"This command only works in WhatsApp"**: Make sure you are in WhatsApp and focused on a message.
* **"No image found in this message"**: Make sure you are focused on a message that contains an image.
* **"API Key Required"**: You need to add your API key in the settings panel.

## License

This add-on is licensed under the GNU General Public License v2.

## Credits and Acknowledgments

* Thanks to the NVDA community for their support and feedback.

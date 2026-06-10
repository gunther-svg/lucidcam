I want to build a desktop application using Python that acts as a real-time AI video restyling tool. It will use the Decart AI "Lucy 2.1" API to transform my local webcam feed in real-time based on text prompts. The application needs a clean, modern UI (inspired by dark-mode mobile apps), must display the live transformed feed, and must output this transformed feed to a Virtual Camera so I can use it in Zoom, OBS, or Teams.
**Required Tech Stack:**
 * **UI Framework:** PyQt6 (for a robust, native desktop UI) along with qasync to handle asynchronous operations natively within the PyQt event loop.
 * **Video Handling:** OpenCV (cv2) for local camera capture if needed, or aiortc if the Decart SDK relies on standard Python WebRTC objects.
 * **Virtual Camera:** pyvirtualcam (to pipe the output frames into a virtual webcam).
 * **API Client:** The official decart Python SDK.
**Core Features & Requirements:**
 1. **API Key Management:** A secure text field in the UI to input the Decart API key, saving it locally (e.g., using .env or a local config file).
 2. **WebRTC Video Pipeline:**
   * Capture the local webcam.
   * Establish a WebRTC connection via the Decart SDK (RealtimeClient.connect).
   * Pipe the transformed remote stream back into the application.
 3. **Virtual Camera Output:** * Take the frames from the on_remote_stream callback.
   * Push them to a pyvirtualcam.Camera instance so the OS recognizes it as a webcam.
 4. **UI/UX Layout:**
   * **Theme:** Modern Dark Mode (slate greys, subtle blue accents).
   * **Video Canvas:** A large central video player showing the live transformed feed. Include a "Play/Connect" overlay button when inactive.
   * **Control Panel (Bottom/Side):**
     * A text input field for custom prompts (e.g., "Change the person's shirt to red").
     * An "Apply" button to trigger await realtime_client.set_prompt().
     * A horizontal scrollable row of "Preset" buttons (e.g., "Albert Stylestein", "Capybara", "Statue of Liberty") that instantly send predefined prompts.
     * Connection status indicator (Disconnected, Connecting..., Live).
**Reference Decart SDK Code:**
Here is the official documentation snippet showing how the SDK works. You must adapt this to work non-blockingly within the PyQt6 + qasync event loop:
```python
from decart import DecartClient, models, SetInput
from decart.realtime import RealtimeClient, RealtimeConnectOptions
from decart.types import ModelState, Prompt

model = models.realtime("lucy-2.1")

# Get user's camera stream (You will need to implement or mock this using aiortc/cv2)
stream = await get_camera_stream(
    audio=True,
    video={
        "frame_rate": model.fps,
        "width": model.width,
        "height": model.height,
    },
)

client = DecartClient(api_key="your-api-key-here")

# Connect to realtime API
realtime_client = await RealtimeClient.connect(
    base_url=client.base_url,
    api_key=client.api_key,
    local_track=stream.video,  # Pass video track
    options=RealtimeConnectOptions(
        model=model,
        on_remote_stream=lambda transformed_stream: (
            # Handle the transformed video in your app and push to pyvirtualcam
            handle_stream(transformed_stream)
        ),
        initial_state=ModelState(
            prompt=Prompt(text="Change the person's shirt to red"),
        ),
    ),
)

# Usage examples to wire to UI buttons:
# await realtime_client.set_prompt("Change the person's hair to blonde")
# await realtime_client.disconnect()

```
**Implementation Steps for the AI:**
 1. **Step 1:** Generate the skeleton for the PyQt6 UI with qasync integration. Include the dark theme styling, the video placeholder, the prompt input bar, and preset buttons.
 2. **Step 2:** Implement the Video/WebRTC handling class. Show me how to properly capture the local webcam track and format it for the local_track argument expected by Decart.
 3. **Step 3:** Implement the handle_stream logic. Extract the frames from the Decart WebRTC remote stream, update the PyQt UI label (using QImage/QPixmap), and simultaneously write to the pyvirtualcam instance.
 4. **Step 4:** Wire the UI buttons to the asynchronous set_prompt and disconnect methods.
Please provide the complete, modular Python code to achieve this. Emphasize robust error handling for the WebRTC connection drops and camera access permissions.

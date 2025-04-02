#include "esp_camera.h"
#include <I2S.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "FS.h"
#include "SD.h"
#include "SPI.h"

#define CAMERA_MODEL_XIAO_ESP32S3
#include "camera_pins.h"

// Hardware definitions
const int buttonPin = 1;
int buttonState;
int imageCount = 1;
bool camera_sign = false;
bool sd_sign = false;
bool isWIFIConnected = false;
int mode = 0;                  // Default mode (0 = photo/audio, 1 = other mode)
bool photoTaken = false;       // Prevents multiple triggers while button is held
unsigned long buttonPressTime; // Stores when the button was first pressed
bool longPressHandled = false; // Ensures long-press action happens only once per press

// Audio recording parameters
#define RECORD_TIME 2
#define WAV_FILE_NAME "recording"
#define SAMPLE_RATE 16000U
#define SAMPLE_BITS 16
#define WAV_HEADER_SIZE 44
#define VOLUME_GAIN 2
uint32_t record_size = (SAMPLE_RATE * SAMPLE_BITS / 8) * RECORD_TIME;

// WiFi credentials
const char* ssid = "Galaxy S23 F2B0";
const char* password = "appikund";

// Server configuration
const char* serverAudioURL = "http://192.168.202.1:8888/uploadAudio";
const char* serverImageURL = "http://192.168.202.1:8888/uploadImage";

void setup() {
  Serial.begin(115200);
  pinMode(buttonPin, INPUT_PULLUP);

  //while(!Serial);

  // Initialize I2S
  I2S.setAllPins(-1, 42, 41, -1, -1);
  if (!I2S.begin(PDM_MONO_MODE, SAMPLE_RATE, SAMPLE_BITS)) {
    Serial.println("Failed to initialize I2S!");
    while(1);
  }

  // Initialize camera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_UXGA;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  
  if(psramFound()){
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  // Camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }
  camera_sign = true;

  // Initialize SD card
  if(!SD.begin(21)){
    Serial.println("Card Mount Failed");
    return;
  }
  sd_sign = true;

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  int wifiTimeout = 20;
  while (WiFi.status() != WL_CONNECTED && wifiTimeout > 0) {
    delay(500);
    Serial.print(".");
    wifiTimeout--;
  }
  
  isWIFIConnected = (WiFi.status() == WL_CONNECTED);
  if(isWIFIConnected) {
    Serial.println("\nWiFi Connected!");
  } else {
    Serial.println("\nWiFi Connection Failed!");
  }

  Serial.println("System ready - press button to capture and send");
}

void sendModeToServer(int currentMode) {
  if(!isWIFIConnected) {
    Serial.println("WiFi not connected - can't send mode");
    return;
  }

  HTTPClient http;
  String serverModeURL = "http://192.168.202.1:8888/uploadMode"; // Adjust URL as needed
  http.begin(serverModeURL);
  http.addHeader("Content-Type", "text/plain");

  String modeString = String(currentMode);
  Serial.printf("Sending mode %d to server... ", currentMode);
  int httpCode = http.POST(modeString);

  http.end();

  if(httpCode == HTTP_CODE_OK) {
    Serial.println("success");
  } else {
    Serial.printf("failed, error: %d\n", httpCode);
  }
}

void loop() {
  if (camera_sign && sd_sign) {
    buttonState = digitalRead(buttonPin);
    static unsigned long buttonPressTime = 0;
    static bool longPressHandled = false;

    if (buttonState == LOW && !photoTaken) {
      // Record when button was first pressed
      if (buttonPressTime == 0) {
        buttonPressTime = millis();
        longPressHandled = false;
      }
      
      // Check if button has been pressed for more than 5 seconds
      if (millis() - buttonPressTime >= 5000 && !longPressHandled) {
        // Change mode (0 to 1 or 1 to 0)
        mode = (mode == 0) ? 1 : 0;
        Serial.print("Mode changed to: ");  // Print mode change
        Serial.println(mode);
        
        if(isWIFIConnected) {
          sendModeToServer(mode);
          }
        longPressHandled = true;
        photoTaken = true; // Prevent photo from being taken
      }
    } 
    else if (buttonState == HIGH) {
      // If button was released before 5 seconds and not in long press mode
      if (buttonPressTime > 0 && millis() - buttonPressTime < 3000 && !longPressHandled) {
        // Generate filenames
        char imageFilename[32];
        char audioFilename[32];
        sprintf(imageFilename, "/image.jpg");
        sprintf(audioFilename, "/%s.wav", WAV_FILE_NAME);
        
        // Capture and save photo
        photo_save(imageFilename);
        
        // Record and save audio
        record_wav(audioFilename);
        
        // Upload files if WiFi connected
        if(isWIFIConnected) {
          uploadFile(imageFilename, serverImageURL, "image/jpeg");
          uploadFile(audioFilename, serverAudioURL, "audio/wav");
        }
      }
      
      // Reset button state
      buttonPressTime = 0;
      photoTaken = false;
      longPressHandled = false;
    }
  }
  delay(100);
}

void photo_save(const char * fileName) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Failed to get camera frame buffer");
    return;
  }
  
  File file = SD.open(fileName, FILE_WRITE);
  if(file.write(fb->buf, fb->len) == fb->len) {
    Serial.printf("Saved: %s (%d bytes)\n", fileName, fb->len);
  } else {
    Serial.println("Write failed");
  }
  
  file.close();
  esp_camera_fb_return(fb);
}

void record_wav(const char *filename) {
  uint8_t *rec_buffer = (uint8_t *)ps_malloc(record_size);
  if (!rec_buffer) {
    Serial.println("malloc failed!");
    return;
  }

  uint32_t sample_size = 0;
  Serial.println("Starting recording...");
  esp_i2s::i2s_read(esp_i2s::I2S_NUM_0, rec_buffer, record_size, &sample_size, portMAX_DELAY);

  if (sample_size == 0) {
    Serial.println("Record Failed!");
    free(rec_buffer);
    return;
  }

  File file = SD.open(filename, FILE_WRITE);
  if(!file) {
    Serial.println("Failed to create audio file");
    free(rec_buffer);
    return;
  }

  // Write WAV header
  uint8_t wav_header[WAV_HEADER_SIZE];
  generate_wav_header(wav_header, record_size, SAMPLE_RATE);
  file.write(wav_header, WAV_HEADER_SIZE);

  // Apply volume gain and write audio data
  for (uint32_t i = 0; i < sample_size; i += SAMPLE_BITS/8) {
    (*(uint16_t *)(rec_buffer+i)) <<= VOLUME_GAIN;
  }
  
  if(file.write(rec_buffer, record_size) == record_size) {
    Serial.printf("Recorded: %s (%d bytes)\n", filename, record_size);
  } else {
    Serial.println("Audio write failed");
  }
  
  file.close();
  free(rec_buffer);
}

void generate_wav_header(uint8_t *wav_header, uint32_t wav_size, uint32_t sample_rate) {
  uint32_t file_size = wav_size + WAV_HEADER_SIZE - 8;
  uint32_t byte_rate = SAMPLE_RATE * SAMPLE_BITS / 8;
  
  const uint8_t set_wav_header[] = {
    'R', 'I', 'F', 'F', file_size, file_size >> 8, file_size >> 16, file_size >> 24,
    'W', 'A', 'V', 'E', 'f', 'm', 't', ' ', 0x10, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x01, 0x00, sample_rate, sample_rate >> 8, sample_rate >> 16, sample_rate >> 24,
    byte_rate, byte_rate >> 8, byte_rate >> 16, byte_rate >> 24, 0x02, 0x00, 0x10, 0x00,
    'd', 'a', 't', 'a', wav_size, wav_size >> 8, wav_size >> 16, wav_size >> 24,
  };
  
  memcpy(wav_header, set_wav_header, sizeof(set_wav_header));
}

void uploadFile(const char* filename, const char* serverURL, const char* contentType) {
  File file = SD.open(filename, FILE_READ);
  if(!file) {
    Serial.println("File not available");
    return;
  }

  HTTPClient http;
  http.begin(serverURL);
  http.addHeader("Content-Type", contentType);
  
  Serial.printf("Uploading %s to %s... ", filename, serverURL);
  int httpCode = http.sendRequest("POST", &file, file.size());
  
  file.close();
  http.end();

  if(httpCode == HTTP_CODE_OK) {
    Serial.println("success");
  } else {
    Serial.printf("failed, error: %d\n", httpCode);
  }
}
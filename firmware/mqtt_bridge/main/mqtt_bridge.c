
#include <stdio.h>
#include <string.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "esp_err.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "mqtt_client.h"

#define TOPIC_PC "mct462/test/from_pc"
#define TOPIC_ESP "mct462/test/from_esp32"

static const char *TAG = "MCT462";
static esp_mqtt_client_handle_t mqtt_client = NULL;
static char broker_uri[96];

// Handle messages from the MQTT broker
static void mqtt_handler(void *args, esp_event_base_t base,
                         int32_t event_id, void *event_data)
{
    esp_mqtt_event_handle_t event = event_data;

    switch ((esp_mqtt_event_id_t)event_id) {
    case MQTT_EVENT_CONNECTED:
        ESP_LOGI(TAG, "MQTT connected");
        esp_mqtt_client_subscribe(event->client, TOPIC_PC, 1);
        break;

    case MQTT_EVENT_DATA:
        ESP_LOGI(TAG, "Received: %.*s",
                 event->data_len, event->data);

        if (event->topic_len == strlen(TOPIC_PC) &&
            strncmp(event->topic, TOPIC_PC,
                    event->topic_len) == 0 &&
            event->data_len == strlen("Hello ESP32") &&
            memcmp(event->data, "Hello ESP32",
                   event->data_len) == 0) {

            esp_mqtt_client_publish(
                event->client,
                TOPIC_ESP,
                "Hello PC",
                0, 1, 0
            );
            ESP_LOGI(TAG, "Reply sent: Hello PC");
        }
        break;

    case MQTT_EVENT_DISCONNECTED:
        ESP_LOGW(TAG, "MQTT disconnected");
        break;

    case MQTT_EVENT_ERROR:
        ESP_LOGE(TAG, "MQTT error");
        break;

    default:
        break;
    }
}

// Handle Wi-Fi connection events
static void wifi_handler(void *arg, esp_event_base_t base,
                         int32_t event_id, void *data)
{
    if (base == WIFI_EVENT &&
        event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    }
    else if (base == WIFI_EVENT &&
             event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGW(TAG, "Wi-Fi lost, reconnecting...");
        esp_wifi_connect();
    }
    else if (base == IP_EVENT &&
             event_id == IP_EVENT_STA_GOT_IP) {

        ESP_LOGI(TAG, "Wi-Fi connected, IP acquired");

        // Start MQTT once; its client manages reconnection.
        if (mqtt_client == NULL) {
            snprintf(broker_uri, sizeof(broker_uri),
                     "mqtt://%s:1883",
                     CONFIG_MCT462_BROKER_IP);

            esp_mqtt_client_config_t mqtt_cfg = {
                .broker.address.uri = broker_uri
            };

            mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
            ESP_ERROR_CHECK(
                esp_mqtt_client_register_event(
                    mqtt_client, ESP_EVENT_ANY_ID,
                    mqtt_handler, NULL
                )
            );
            ESP_ERROR_CHECK(
                esp_mqtt_client_start(mqtt_client)
            );
        }
    }
}

void app_main(void)
{
    esp_err_t err = nvs_flash_init();

    if (err == ESP_ERR_NVS_NO_FREE_PAGES ||
        err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID,
        wifi_handler, NULL
    ));
    ESP_ERROR_CHECK(esp_event_handler_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP,
        wifi_handler, NULL
    ));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = CONFIG_MCT462_WIFI_SSID,
            .password = CONFIG_MCT462_WIFI_PASSWORD
        }
    };

    ESP_ERROR_CHECK(
        esp_wifi_set_mode(WIFI_MODE_STA)
    );
    ESP_ERROR_CHECK(
        esp_wifi_set_config(WIFI_IF_STA, &wifi_config)
    );
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "MCT462 communication started");
}

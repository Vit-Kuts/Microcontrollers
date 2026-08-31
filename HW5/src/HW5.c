#include "HW5.h"

#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <usbd_cdc_if.h>

HW5_Struct HW5_Data;

HW5_status HW5_Init() {
  HW5_Data.busy_flag = 0;
  HW5_Data.rx_flag = 0;
  memset(HW5_Data.rx_buf, 0, RX_BUF_SIZE);
  memset(HW5_Data.command, 0, MAX_CMD_SIZE);
  memset(HW5_Data.word_count, 0, MAX_WORD_SYMBOL_COUNT);
  return (HW5_OK);
}

static HW5_status Check();

HW5_Struct HW5_GetHW5_Data() { return HW5_Data; }

HW5_status HW5_IntelHexParse(uint8_t *buf, uint32_t len) {
  HW5_Init();
  memcpy(HW5_Data.rx_buf, buf, len);
  // HW5_Data.rx_buf[len] = '\0';

  int parsed_fields =
      sscanf((char *)HW5_Data.rx_buf,
             "%" TO_STR(LIMIT_CMD) "s %" TO_STR(LIMIT_ADDR) "s %" TO_STR(
                 LIMIT_SYMBOL_COUNT) "s",
             HW5_Data.command, HW5_Data.addr, HW5_Data.word_count);

  if (parsed_fields != 3) {
    return HW5_ERR;
  }

  HW5_Data.rx_flag = 1;
  return HW5_OK;
}

void HW5_Handler() {
  if (HW5_Data.rx_flag) {
    if (Check() == HW5_ERR) {
      char buffer[20];
      snprintf(buffer, sizeof(buffer), "ERROR!\n");
      CDC_Transmit_FS((uint8_t *)buffer, strlen(buffer));
      return;
    }

    HW5_Data.busy_flag = 1;
    uint32_t addr = 0, count = 0;
    addr = strtoul(HW5_Data.addr, NULL, 16);
    count = strtoul(HW5_Data.word_count, NULL, 10);

    volatile uint32_t *pointer = (volatile uint32_t *)addr;
    uint32_t offset = 0;
    uint32_t value_in_memory[count];

    char buffer[2048];
    for (int i = 0; i < count; i++) {
      value_in_memory[i] = *pointer;
      pointer++;
      snprintf(buffer + offset, sizeof(buffer) - offset, ":0x%08X\r\n",
               (unsigned int)value_in_memory[i]);
      offset = strlen(buffer);
    }

    CDC_Transmit_FS((uint8_t *)buffer, strlen(buffer));
    HW5_Data.rx_flag = 0;
    HW5_Data.busy_flag = 0;
  }
}

static HW5_status Check() {
  if (strcmp(HW5_Data.command, "get_hex") != 0) {
    HW5_Init();
    return HW5_ERR;
  }

  if (HW5_Data.addr[0] == '\0') {
    HW5_Init();
    return HW5_ERR;
  }

  int i = 0;
  if (HW5_Data.addr[0] == '0' &&
      (HW5_Data.addr[1] == 'x' || HW5_Data.addr[1] == 'X')) {
    i = 2;
    if (HW5_Data.addr[i] == '\0') {
      HW5_Init();
      return HW5_ERR;
    }
  }

  for (; HW5_Data.addr[i] != '\0'; i++) {
    if (!isxdigit((unsigned char)HW5_Data.addr[i])) {
      HW5_Init();
      return HW5_ERR;
    }
  }

  if (HW5_Data.word_count[0] == '\0') {
    HW5_Init();
    return HW5_ERR;
  }

  for (int j = 0; HW5_Data.word_count[j] != '\0'; j++) {
    if (!isdigit((unsigned char)HW5_Data.word_count[j])) {
      HW5_Init();
      return HW5_ERR;
    }
  }

  return HW5_OK;
}
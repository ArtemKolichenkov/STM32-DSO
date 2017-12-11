#include "main.h"
#include "stm32f4xx_hal.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"

#define ADC_BUFFER_LENGTH_TRIPLE 9999
#define ADC_BUFFER_LENGTH_SINGLE 5555
#define CH1_ENABLED 1
#define CH2_ENABLED 1
#define LOGIC_ENABLED 1
#define CH1_DISABLED 0
#define CH2_DISABLED 0
#define LOGIC_DISABLED 0

// ADC and DMA structures declaration
ADC_HandleTypeDef hadc1;
ADC_HandleTypeDef hadc2;
ADC_HandleTypeDef hadc3;
DMA_HandleTypeDef hdma_adc1;

uint8_t rxdata[3] = {0, 0, 0};
uint8_t ADCBufferTriple[ADC_BUFFER_LENGTH_TRIPLE];
uint8_t ADCBufferSingle1[ADC_BUFFER_LENGTH_SINGLE];
uint8_t ADCBufferSingle2[ADC_BUFFER_LENGTH_SINGLE];
uint8_t LogicBuffer[14400];

void SystemClock_Config(void);
void Error_Handler(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void TripleADC_Init(void);

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* AdcHandle)
{
	if (AdcHandle == &hadc1)
	{
		CDC_Transmit_FS(ADCBufferSingle1, ADC_BUFFER_LENGTH_SINGLE);
	}
	else {
		CDC_Transmit_FS(ADCBufferSingle2, ADC_BUFFER_LENGTH_SINGLE);
	}
}

void ADC_MultiModeDMAConvCplt(DMA_HandleTypeDef *hdma)
{
	ADC_MultiModeTypeDef multimode;
	
	HAL_ADCEx_MultiModeStop_DMA(&hadc1);
	HAL_ADC_Stop(&hadc3);	
	HAL_ADC_Stop(&hadc2);
	multimode.Mode = ADC_MODE_INDEPENDENT;
	multimode.DMAAccessMode = ADC_DMAACCESSMODE_DISABLED;
	multimode.TwoSamplingDelay = ADC_TWOSAMPLINGDELAY_5CYCLES;
	if (HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode) != HAL_OK)
	{
		Error_Handler();
	}
	
	HAL_Delay(100);
	multimode.Mode = ADC_TRIPLEMODE_INTERL;
	multimode.DMAAccessMode = ADC_DMAACCESSMODE_3;
	multimode.TwoSamplingDelay = ADC_TWOSAMPLINGDELAY_5CYCLES;
	if (HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode) != HAL_OK)
	{
		Error_Handler();
	}
	CDC_Transmit_FS(ADCBufferTriple, ADC_BUFFER_LENGTH_TRIPLE);
}

void ACQUIRE_CHANNEL_1(void);
void ACQUIRE_CHANNEL_1_TRIPLE(void);
void ACQUIRE_CHANNEL_2(void);
void ACQUIRE_LOGIC(void);

int main(void)
{
	// ADC MultiMode structure for Triple Interleaved mode
	ADC_MultiModeTypeDef multimode;
	
  HAL_Init(); // Initialization of hardware abstraction library
  SystemClock_Config(); // Sytem clocks initialization
  MX_GPIO_Init(); // GPIO initialization
  MX_DMA_Init(); // DMA initialization
  MX_USB_DEVICE_Init(); // USB driver initialization
	TripleADC_Init(); // ADC initialization
	HAL_Delay(250); // Delay for initialization to propagate safely
	
  while (1)
  {
		if (rxdata[0] == CH1_ENABLED)
		{
			if (rxdata[1] == CH2_ENABLED)
			{
				if (rxdata[2] == LOGIC_ENABLED)
				{
					ACQUIRE_CHANNEL_1();
					ACQUIRE_CHANNEL_2();
					ACQUIRE_LOGIC();
				}
				ACQUIRE_CHANNEL_1();
				ACQUIRE_CHANNEL_2();
			}
			else if (rxdata[2] == LOGIC_ENABLED)
			{
				ACQUIRE_CHANNEL_1();
				ACQUIRE_LOGIC();
			}
			ACQUIRE_CHANNEL_1_TRIPLE();
		}
		else if (rxdata[0] == CH1_DISABLED && rxdata[1] == CH2_ENABLED)
		{
			if (rxdata[2] == LOGIC_ENABLED)
			{
				ACQUIRE_CHANNEL_2();
				ACQUIRE_LOGIC();
			}
			ACQUIRE_CHANNEL_2();
		}
		else if (rxdata[0] == CH1_DISABLED && rxdata[1] == CH2_DISABLED && rxdata[2] == LOGIC_ENABLED)
		{
			ACQUIRE_LOGIC();
		}		
  }
}

void ACQUIRE_CHANNEL_1(void) 
{
	HAL_ADC_Start_DMA(&hadc1, (uint32_t*) ADCBufferSingle1, ADC_BUFFER_LENGTH_SINGLE);
}

void ACQUIRE_CHANNEL_2(void) 
{
	HAL_ADC_Start_DMA(&hadc2, (uint32_t*) ADCBufferSingle2, ADC_BUFFER_LENGTH_SINGLE);
}

void ACQUIRE_CHANNEL_1_TRIPLE(void) 
{	
	HAL_ADC_Start(&hadc3);
	HAL_ADC_Start(&hadc2);
	HAL_ADCEx_MultiModeStart_DMA(&hadc1, (uint32_t*) &ADCBufferTriple, ADC_BUFFER_LENGTH_TRIPLE);
}

void ACQUIRE_LOGIC(void) 
{
	for (uint32_t i = 0; i < 14400; i++)
	{
		LogicBuffer[i+i*7] = HAL_GPIO_ReadPin(GPIOE, GPIO_PIN_7);
		LogicBuffer[i+i*7+1] = HAL_GPIO_ReadPin(GPIOE, GPIO_PIN_8);
		LogicBuffer[i+i*7+2] = HAL_GPIO_ReadPin(GPIOE, GPIO_PIN_9);
		LogicBuffer[i+i*7+3] = HAL_GPIO_ReadPin(GPIOE, GPIO_PIN_10);
		LogicBuffer[i+i*7+4] = HAL_GPIO_ReadPin(GPIOE, GPIO_PIN_11);
		LogicBuffer[i+i*7+5] = HAL_GPIO_ReadPin(GPIOE, GPIO_PIN_12);
		LogicBuffer[i+i*7+6] = HAL_GPIO_ReadPin(GPIOE, GPIO_PIN_13);
		LogicBuffer[i+i*7+7] = HAL_GPIO_ReadPin(GPIOE, GPIO_PIN_14);
	}
	CDC_Transmit_FS(LogicBuffer, 14400);
}

void SystemClock_Config(void)
{

  RCC_OscInitTypeDef RCC_OscInitStruct;
  RCC_ClkInitTypeDef RCC_ClkInitStruct;

    /**Configure the main internal regulator output voltage 
    */
  __HAL_RCC_PWR_CLK_ENABLE();

  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE3);

    /**Initializes the CPU, AHB and APB busses clocks 
    */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLM = 4;
  RCC_OscInitStruct.PLL.PLLN = 72;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
  RCC_OscInitStruct.PLL.PLLQ = 3;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

    /**Initializes the CPU, AHB and APB busses clocks 
    */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }

    /**Configure the Systick interrupt time 
    */
  HAL_SYSTICK_Config(HAL_RCC_GetHCLKFreq()/1000);

    /**Configure the Systick 
    */
  HAL_SYSTICK_CLKSourceConfig(SYSTICK_CLKSOURCE_HCLK);

  /* SysTick_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(SysTick_IRQn, 0, 0);
}


static void TripleADC_Init(void)
{
	ADC_MultiModeTypeDef multimode;
	ADC_ChannelConfTypeDef sConfig;
	
	sConfig.Channel = ADC_CHANNEL_3;
  sConfig.Rank = 1;
  sConfig.SamplingTime = ADC_SAMPLETIME_3CYCLES;

	// ----------------------- ADC3 configuration
	hadc3.Instance = ADC3;
  hadc3.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV2;
  hadc3.Init.Resolution = ADC_RESOLUTION_8B;
  hadc3.Init.ScanConvMode = DISABLE;
  hadc3.Init.ContinuousConvMode = ENABLE;
  hadc3.Init.DiscontinuousConvMode = DISABLE;
  hadc3.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc3.Init.NbrOfConversion = 1;
  hadc3.Init.DMAContinuousRequests = DISABLE;
  hadc3.Init.EOCSelection = DISABLE;
  if (HAL_ADC_Init(&hadc3) != HAL_OK)
  {
    Error_Handler();
  }
	
  if (HAL_ADC_ConfigChannel(&hadc3, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
	
	// ----------------------- ADC2 Configuration
	
	hadc2.Instance = ADC2;
  hadc2.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV2;
  hadc2.Init.Resolution = ADC_RESOLUTION_8B;
  hadc2.Init.ScanConvMode = DISABLE;
  hadc2.Init.ContinuousConvMode = ENABLE;
  hadc2.Init.DiscontinuousConvMode = DISABLE;
  hadc2.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc2.Init.NbrOfConversion = 1;
  hadc2.Init.DMAContinuousRequests = DISABLE;
  hadc2.Init.EOCSelection = DISABLE;
  if (HAL_ADC_Init(&hadc2) != HAL_OK)
  {
    Error_Handler();
  }	

  if (HAL_ADC_ConfigChannel(&hadc2, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
	
	// ----------------------- ADC1 Configuration
	hadc1.Instance = ADC1;
  hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV2;
  hadc1.Init.Resolution = ADC_RESOLUTION_8B;
  hadc1.Init.ScanConvMode = DISABLE;
  hadc1.Init.ContinuousConvMode = ENABLE;
  hadc1.Init.DiscontinuousConvMode = DISABLE;
  hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
  hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
  hadc1.Init.NbrOfConversion = 1;
  hadc1.Init.DMAContinuousRequests = DISABLE;
  hadc1.Init.EOCSelection = DISABLE;
  if (HAL_ADC_Init(&hadc1) != HAL_OK)
  {
    Error_Handler();
  }

  if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK)
  {
    Error_Handler();
  }
	
  multimode.Mode = ADC_TRIPLEMODE_INTERL;
  multimode.DMAAccessMode = ADC_DMAACCESSMODE_3;
  multimode.TwoSamplingDelay = ADC_TWOSAMPLINGDELAY_5CYCLES;
  if (HAL_ADCEx_MultiModeConfigChannel(&hadc1, &multimode) != HAL_OK)
  {
    Error_Handler();
  }
	
}

/** 
  * Enable DMA controller clock
  */
static void MX_DMA_Init(void) 
{
  /* DMA controller clock enable */
  __HAL_RCC_DMA2_CLK_ENABLE();

  /* DMA interrupt init */
  /* DMA2_Stream0_IRQn interrupt configuration */
  HAL_NVIC_SetPriority(DMA2_Stream0_IRQn, 0, 0);
  HAL_NVIC_EnableIRQ(DMA2_Stream0_IRQn);

}


static void MX_GPIO_Init(void)
{

  GPIO_InitTypeDef GPIO_InitStruct;

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOH_CLK_ENABLE();
  __HAL_RCC_GPIOE_CLK_ENABLE();
	

  /*Configure GPIO pins : PE7 PE8 PE9 PE10 
                           PE11 PE12 PE13 PE14 */
  GPIO_InitStruct.Pin = GPIO_PIN_7|GPIO_PIN_8|GPIO_PIN_9|GPIO_PIN_10 
                          |GPIO_PIN_11|GPIO_PIN_12|GPIO_PIN_13|GPIO_PIN_14;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);
}




void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler */
  /* User can add his own implementation to report the HAL error return state */
  while(1) 
  {
  }
  /* USER CODE END Error_Handler */ 
}

#ifdef USE_FULL_ASSERT

#endif

/**
  * @}
  */ 

/**
  * @}
*/ 

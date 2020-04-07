""" file DFRobot_Sensor.py
  #
  # 定义DFRobot_Sensor 类的基础结构，基础方法的实现
  #
  # @copyright   Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
  # @licence     The MIT License (MIT)
  # @author      Alexander(ouki.wang@dfrobot.com)
  # version  V1.0
  # date  2017-10-9
  # @get from https://www.dfrobot.com
  # @url https://github.com/DFRobot/DFRobot_Sensor
"""

import sys
import smbus
import logging
from ctypes import *

logger = logging.getLogger()
logger.setLevel(logging.INFO)  #显示所有的打印信息
#logger.setLevel(logging.FATAL)#如果不想显示过多打印，只打印错误，请使用这个选项
ph = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - [%(filename)s %(funcName)s]:%(lineno)d - %(levelname)s: %(message)s")
ph.setFormatter(formatter) 
logger.addHandler(ph)

DFRobot_Sensor_IIC_ADDR = 0x66 #芯片IIC地址，无变化地址功能
DFRobot_Sensor_ID = 0xDF  #芯片IIC地址，无变化地址功能


COLOR_RGB565_NAVY    =  0x000F      # 深蓝色  
COLOR_RGB565_DGREEN  =  0x03E0      # 深绿色  
COLOR_RGB565_BLACK   =  0x0000      # 黑色    
COLOR_RGB565_DCYAN   =  0x03EF      # 深青色  
COLOR_RGB565_PURPLE  =  0x780F      # 紫色  
COLOR_RGB565_MAROON  =  0x7800      # 深红色      
COLOR_RGB565_OLIVE   =  0x7BE0      # 橄榄绿      
COLOR_RGB565_LGRAY   =  0xC618      # 灰白色
COLOR_RGB565_DGRAY   =  0x7BEF      # 深灰色      
COLOR_RGB565_BLUE    =  0x001F      # 蓝色    
COLOR_RGB565_GREEN   =  0x07E0      # 绿色          
COLOR_RGB565_CYAN    =  0x07FF      # 青色  
COLOR_RGB565_RED     =  0xF800      # 红色       
COLOR_RGB565_MAGENTA =  0xF81F      # 品红    
COLOR_RGB565_YELLOW  =  0xFFE0      # 黄色    
COLOR_RGB565_WHITE   =  0xFFFF      # 白色  

class DFRobot_Sensor:
  _SENSOR_ADDR_LED    = 0 #LED控制地址  这里的描述从芯片手册上抄写
  _SENSOR_ADDR_DATA   = 2 #组合数据地址  这里的描述从芯片手册上抄写
  _SENSOR_ADDR_CONFIG = 3 #配置寄存器地址 这里的描述从芯片手册上抄写
  _SENSOR_ADDR_ID     = 4 #芯片ID寄存器地址 这里的描述从芯片手册上抄写


  ERR_OK         =    0      #无错误
  ERR_DATA_BUS   =   -1      #数据总线错误
  ERR_IC_VERSION =   -2      #芯片版本不匹配

  eNormalPower = 0, # 正常功耗模式，功耗范围20mW-60mW，可以搭配任意采集速度eSpeedMode_t和采集精度ePrecisionMode_t 
  eLowPower = 1,   # 低功耗模式，功耗范围2mW-4mW, 注意在低功耗模式下，采集速度eSpeedMode_t只能搭配eNormalSpeed，采集精度ePrecisionMode_t只能搭配eLowPrecision和eNomalPrecision

  eNormalSpeed = 0<<1, # 正常采集速度，可以和任意精度搭配使用
  eHighSpeed = 1<<1,   # 高速采集模式，采集周期10ms，可以进入低功耗，可以配置为eLowPrecision和eNomalPrecision两种精度模式
  
  eLowPrecision   = 0<<2, # 低精度，精度大概在xxx，在低精度模式下，可以进入低功耗
  eNomalPrecision = 1<<2, # 正常精度，精度大概在xxx，在正常精度模式下，可以进入低功耗
  eHighPrecision  = 2<<2, # 高精度，精度大概在xxx，在高精度模式下，采集速率会降低，采集周期100ms，不能进入低功耗
  eUltraPrecision = 3<<2, # 超高精度，精度大概在xxx，在超高精度模式下，采集速率会极低，采集周期1000ms，不能进入低功耗
  '''
   #这里从数据手册上抄写关于这个寄存器的描述
     # ------------------------------------------------------------------------------------------
     # |    b7    |    b6    |    b5    |    b4    |    b3    |    b2    |    b1     |    b0    |
     # ------------------------------------------------------------------------------------------
     # |                 声音强度                  |                  光线强度                  |
     # ------------------------------------------------------------------------------------------
   '''
  class CombinedData(Structure):
    _pack_ = 1
    _fields_=[('light',c_ubyte,4),
            ('sound',c_ubyte,4)]
    def __init__(self, light=0, sound = 2):
      self.light = light
      self.sound = sound

  class Color(Structure):
    _pack_ = 1
    _fields_=[('b',c_ubyte,5),
            ('g1',c_ubyte,3),
            ('g2',c_ubyte,3),
            ('r',c_ubyte,5)]
    def __init__(self, r=0, g=0, b=0):
      self.r = r>>3
      self.g = g>>2
      self.b = b>>3
      self.g1 = g>>5
      self.g2 = (g>>2)&7

    def update(self):
      self.g = self.g1 + self.g2*8

    def set_list(self, data):
      buf = (c_ubyte * len(data))()
      for i in range(len(data)):
        buf[i] = data[i]
      memmove(addressof(self), addressof(buf), len(data))

    def get_list(self):
      return list(bytearray(string_at(addressof(self),sizeof(self))))

  '''
   #这里从数据手册上抄写关于这个寄存器的描述
     # -----------------------------------------------------------------------------------------
     # |    b7    |    b6    |    b5    |    b4    |    b3    |    b2   |    b1     |    b0    |
     # -----------------------------------------------------------------------------------------
     # |   ready  |         reversed               |      precision     | highspeed | lowpower |
     # -----------------------------------------------------------------------------------------
     #
     #上电后，ready位默认为1，不可更改
  '''
  class Mode(Structure):
    _pack_ = 1
    _fields_=[('lowpower',c_ubyte,1), #上电为0，1：低功耗模式 0：正常功耗模式
            ('highspeed',c_ubyte,1),  #上电为0，1：高速模式 0：正常速度模式
            ('precision',c_ubyte,2),  #上电为0，0：低精度模式，1：正常精度模式，2：高精度模式，3：超高精度模式
            ('reserved',c_ubyte,2),   #上电为0
            ('ready',c_ubyte,1)]      #上电为0，1：低功耗模式 0：正常功耗模式
    def __init__(self, lowpower=0, highspeed=0, precision=0, ready=0):
      self.lowpower = lowpower
      self.highspeed = highspeed
      self.precision = precision
      self.ready = ready

    def set_list(self, data):
      buf = (c_ubyte * len(data))()
      for i in range(len(data)):
        buf[i] = data[i]
      memmove(addressof(self), addressof(buf), len(data))

    def get_list(self):
      return list(bytearray(string_at(addressof(self),sizeof(self))))

  def __init__(self, mode):
    self._mode = mode

  def begin(self):
    id = self.read_reg(_SENSOR_ADDR_ID)
    if id == None :
      logger.warning("ERR_DATA_BUS")
      return ERR_DATA_BUS;

    logger.info("id=%d"%(id[0]))

    if id[0] != _DFRobot_Sensor_ID:
      return ERR_IC_VERSION;

    self.write_reg(_SENSOR_ADDR_CONFIG, [self._mode])
    return ERR_OK;

  def sound_strength_db(self):
    data=CombinedData()
    value = self.read_reg(_SENSOR_ADDR_DATA)
    data.set_list(value)
    logger.info("sound=%d"%(data.sound))
    return data.sound << 3

  def light_strength_lux(self):
    data = CombinedData()
    value = self.read_reg(_SENSOR_ADDR_DATA)
    data.set_list(value)
    logger.info("light reg raw data is %d"%(data.light))
    return data.light * 10000

  def set_led(self, r, g, b):
    data = Color(b=b>>3,g=g>>2,r=r>>3)
    write_reg(_SENSOR_ADDR_LED, data.get_list())

  def set_led(self, color):
    data = [color&0xff, (color>>8)&0xff]
    write_reg(_SENSOR_ADDR_LED, data)

  def switch_mode(self, mode)
    data = [mode&0xff]
    write_reg(SENSOR_ADDR_CONFIG, data);


class DFRobot_Sensor_IIC(DFRobot_Sensor):
  def __init__(self, bus, mode):
    self.i2cbus=smbus.SMBus(bus)
    self.i2c_addr = DFRobot_Sensor_IIC_ADDR
    super().__init__(mode)

  def begin(self):
    return super().begin()

  def write_reg(self, reg, value):
    self.i2cbus.write_i2c_block_data(self.i2c_addr, reg, value)

  def read_reg(self, reg):
    return self.i2cbus.read_i2c_block_data(self.i2c_addr, reg) 

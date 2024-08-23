import logging
import threading
import time
import sys
from enum import Enum

#try:
#    from src.TMC_2209.TMC_2209_StepperDriver import *
#    from src.TMC_2209._TMC_2209_GPIO_board import Board
#except ModuleNotFoundError:
#    from TMC_2209.TMC_2209_StepperDriver import *
#    from TMC_2209._TMC_2209_GPIO_board import Board


from abc import ABC, abstractmethod

class Motor(ABC):
	abstractmethod
	def __init__(self, enGPIO, stepGPIO, dirGPIO, serial, name):
		pass
		
		
			
	@abstractmethod
	def move(self, numSteps, direction, stepInterpolation):	
		pass		
		
	@abstractmethod
	def shutdown(self):
		pass




#DUMMY IMPLEMENTATION OF TMC Motor for when developing on windows
class DummyMotor(Motor):

	def __init__(self, enGPIO, stepGPIO, dirGPIO, serial, name):
		print ("Initialising dummy motor with ", enGPIO, stepGPIO, dirGPIO, serial, name)
			
	
	def move(self, numSteps, direction, stepInterpolation):	
		print ("Moving dummy motor ", numSteps, direction, stepInterpolation)
		

	def shutdown(self):
		print("Shutting down dummy motor")	
		
		

	



class TMCMotor(Motor):



	def __init__(self, enGPIO, stepGPIO, dirGPIO, serial, name):		
		
		
		
		#if self.motor is not None:
		#	self.motor.stop()
		self.motor = None  # gc the previous threads
        
		# initialise motor class from TMC_2209
		print("Started initialising motor ",enGPIO, stepGPIO, dirGPIO, serial, flush=True)
		self.motor = TMC_2209(enGPIO, stepGPIO, dirGPIO,serialport=serial)
       
		# fixed
		self.motor.set_direction_reg(False)  #False = CCW; True = CW
		self.motor.set_current(300)
		self.motor.set_interpolation(True) 
		self.motor.set_spreadcycle(False)
		self.motor.set_internal_rsense(False)
		self.motor.set_acceleration_fullstep(1000)
		
		#print("ATtempting dummy run during initialisation ")
		self.motor.set_max_speed_fullstep(25)
		self.motor.set_motor_enabled(True)
		
		self.lastDirection = None
		self.lastInterpolation = None
		#self.motor.run_to_position_steps(400)                             #move to position 400
		#self.motor.run_to_position_steps(0)            
                
        
		# final
		self.motor.read_ioin()
		print("Finished initialisation of motor ", flush=True)
  
		return  



	
	def move(self, numSteps, direction, stepInterpolation):	
		print ("Moving motor ", numSteps, direction, stepInterpolation)
		
		match direction:
			case "CCW": 
				direction = "True"
			case "CW": 
				direction = "False"
        
		
		
		if (self.lastDirection == None):
			self.lastDirection = direction
			print ("Setting direction for first time",direction)
			self.motor.set_direction_reg(direction=='True') 
		elif not(self.lastDirection == direction):
			self.lastDirection = direction
			print ("Setting direction because it has switched",direction)
			self.motor.set_direction_reg(direction=='True') 

		
		if (self.lastInterpolation == None):
			print ("Setting interpolation for first time")
			self.lastInterpolation = stepInterpolation
			self.motor.set_microstepping_resolution(int(stepInterpolation))    
		elif not(self.lastInterpolation == stepInterpolation):
			self.lastInterpolation = stepInterpolation
			print ("Setting interpolation")
			self.motor.set_microstepping_resolution(int(stepInterpolation))    
			print ("Finish setting interpolation")
		
		
		#print ("Started actual move")
		self.motor.run_to_position_steps(numSteps, MovementAbsRel.RELATIVE)
		#print ("Finished actual move")

		#print ("Finished moving motor ", numSteps, direction, stepInterpolation)

	def shutdown(self):
		self.motor.set_motor_enabled(False)
        
	

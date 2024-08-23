# Created on : Dec 26, 2023, 2:39:28 PM
# Author     : Patrick Abela

import logging
import threading
import time
import sys

from enum import Enum

from AbstractMotor import DummyMotor,TMCMotor
from flask import Flask, abort
from flask import request
from flask_restful import Api, Resource
from flask import jsonify
import sqlite3

app = Flask(__name__)
api = Api(app)


#global variables

# basic setup
path = '127.0.0.1';

#classwide states
panMotorState= 'NOT_INITIALISED'
tiltMotorState= 'NOT_INITIALISED'
panMovementState='STATIONARY'
tiltMovementState='STATIONARY'


#database initialisation
try: 
	connection=sqlite3.connect("lunaves.db")
	cursor = connection.cursor()
	cursor.execute("CREATE TABLE if not exists session(id, pan1,pan2, pan4, pan8, pan16, pan32, pan64, pan128, pan256, panDirection,tilt1,tilt2, tilt4, tilt8, tilt16, tilt32, tilt64, tilt128, tilt256, tiltDirection )")
finally:
	cursor.close()
	connection.close()

panMotor=None
tiltMotor=None


def setPath(p_path):
	global path
	path = p_path
	
	


def activeSession():
	try:
		connection=sqlite3.connect("lunaves.db")
		cursor = connection.cursor()
		result = cursor.execute("SELECT id FROM session where id=1")
		row = result.fetchone()
		if row is not None:
			return True
		else: 	
			return False
	finally:
		#close open cursor and commit  
		cursor.close()
		connection.commit()	



@app.route('/pantilt', methods=['POST', 'DELETE', 'GET'])
def pantilt():
	global panMotorState, tiltMotorState, panMovementState, tiltMovementState,panMotor, tiltMotor
	try:
		connection=sqlite3.connect("lunaves.db")
		cursor = connection.cursor()
		dummy=False
		
		if request.method == 'POST':
			if panMotorState == 'NOT_INITIALISED' and tiltMotorState == 'NOT_INITIALISED' :	
				data = request.get_json()
				
				if dummy:
					
					panMotor = DummyMotor()
					tiltMotor = DummyMotor()
				else :
					print ("WS: CREATING TMC MOTOR")
					panMotor = DummyMotor(enGPIO=int(data.get('panEnGPIO')), stepGPIO=int(data.get('panStepGPIO')), dirGPIO=int(data.get('panDirGPIO')), serial=data.get('panSerial'), name="pan")
					#TMCMotor(enGPIO=int(data.get('panEnGPIO')), stepGPIO=int(data.get('panStepGPIO')), dirGPIO=int(data.get('panDirGPIO')), serial=data.get('panSerial'), name="pan")
					
					tiltMotor = DummyMotor(enGPIO=int(data.get('tiltEnGPIO')), stepGPIO=int(data.get('tiltStepGPIO')), dirGPIO=int(data.get('tiltDirGPIO')), serial=data.get('tiltSerial'), name="pan")
					#TMCMotor(enGPIO=int(data.get('tiltEnGPIO')), stepGPIO=int(data.get('tiltStepGPIO')), dirGPIO=int(data.get('tiltDirGPIO')), serial=data.get('tiltSerial'), name="pan")
					

				panMotorState='INITIALISED'
				tiltMotorState='INITIALISED'
				panMovementState='STATIONARY'
				tiltMovementState='STATIONARY'
				
			
				return ""
			else:
				abort(403,'{"message":"Pantilt is already initialised"}')
		elif request.method == 'DELETE':
			if (activeSession()):
				#delete any outstanding sessions
				cursor.execute('DELETE FROM session where id=1')
				
			panMotorState= 'NOT_INITIALISED'
			tiltMotorState= 'NOT_INITIALISED'
			panMovementState='STATIONARY'
			tiltMovementState='STATIONARY'
			
			panMotor.shutdown()
			tiltMotor.shutdown()
			del panMotor
			del tiltMotor
			
			return ""
		elif request.method == 'GET':
			return jsonify(
			{
				"panMotorState": panMotorState,
				"panMovementState": panMovementState, 
				"tiltMotorState": tiltMotorState,
				"tiltMovementState": tiltMovementState
			}
			)
	finally:
		#close open cursor and commit  
		cursor.close()
		connection.commit()
	return "ok"
	


 
@app.route('/pantilt/activesession', methods=['POST', 'DELETE', 'GET'])
def activesession():

	try:
		connection=sqlite3.connect("lunaves.db")
		cursor = connection.cursor()
		
		if request.method == 'POST':

			if not (activeSession()):
				#create a fresh session
				print ("POST session: Did not find session and hence creating a new session entry")	
				cursor.execute('INSERT INTO session values (1, 0,0, 0, 0, 0, 0, 0, 0, 0, "CW",0,0, 0, 0, 0, 0,0, 0, 0,"CW") ')
				connection.commit()
				return ""
			else:
				#overrwite any existing data in session - no need to give error
				print ("POST session: Found a session and hence we are updating it with fresh data")	
				cursor.execute('UPDATE session SET pan1=0,pan2=0, pan4=0, pan8=0, pan16=0, pan32=0, pan64=0, pan128=0, pan256=0, panDirection="CW",tilt1=0,tilt2=0, tilt4=0, tilt8=0, tilt16=0, tilt32=0,tilt64=0, tilt128=0, tilt256=0,tiltDirection="CW" WHERE id=1')
				connection.commit()
				return ""
		elif request.method == 'DELETE':
				#remove notion of session completely
				print ("DELETE session: Deleting session")	
				cursor.execute('DELETE FROM session where id=1')
				connection.commit()
				return ""
		elif request.method == 'GET':
			if activeSession():
				print ("GET session:  found a session")	
				res = cursor.execute("SELECT* FROM session WHERE id=1")
				r = res.fetchone()
				
				#the total movement depends on the fractional step movements added up
				totalPanDelta = (r[1]+r[2]/2 +r[3]/4 + r[4]/8 + r[5]/16 +r[6]/32 + r[7]/64 + r[8]/128 + r[9]/256)
				adjustedPanDirection=r[10]


				adjustedTiltDirection=r[20]
				totalTiltDelta = (r[11]+r[12]/2 +r[13]/4 + r[14]/8 + r[15]/16 +r[16]/32 + r[17]/64 + r[18]/128 + r[19]/256)
				
				#avoid returning -ve movements	
				if (totalPanDelta < 0):
					totalPanDelta = totalPanDelta * -1
					if r[10] == 'CCW':
						adjustedPanDirection = 'CW'
					else: 
						adjustedPanDirection = 'CCW'
				
				
				if (totalTiltDelta < 0):
					totalTiltDelta = totalTiltDelta * -1
					if r[20] == 'CCW':
						adjustedTiltDirection = 'CW'
					else: 
						adjustedTiltDirection = 'CCW'

				
				return jsonify(
				{
					"netPanSteps":  totalPanDelta,
					"netPanDirection":  adjustedPanDirection,
					"netTiltSteps": totalTiltDelta,
					"netTiltDirection": adjustedTiltDirection
				}
				)
			else:
				print ("GET session:  - did not find any session")	
				abort(404,'{"message":"No active session resource"}')
	finally:
		#close open cursor and commit  
		cursor.close()
		connection.commit()

	return "ok"
 
 
 
 
 
 
 

 
 
 
@app.route('/pantilt/slew', methods=['POST', 'DELETE', 'GET'])
def slewMovement():
	
	global panMotorState, tiltMotorState, panMovementState, tiltMovementState,panMotor, tiltMotor,panDirection, panInterpolation, tiltDirection, tiltInterpolation
	
	def _slew_pan_thread():
		try:
			panConnection=sqlite3.connect("lunaves.db")
			panCursor = panConnection.cursor()		 
			while (panMovementState == 'SLEWING'):
				step = 1
				panMotor.move(step, panDirection, panInterpolation)
				
				#if moving in current direction, just increment counter, else decrement
				result = panCursor.execute ("SELECT panDirection from SESSION where id=1")
				motorPanDirection = result.fetchone()[0]
				if panDirection == motorPanDirection :
					print("same pan direction",panDirection, motorPanDirection)
					delta = "+" + str(step)
				else:
					print("different pan direction",panDirection, motorPanDirection)
					delta = "-" + str(step )
				
				
				#update database here
				#UPDATE {table} SET {column} = {column} + {value} WHERE {condition}
				print ("PAN INTERPOLATION: ", panInterpolation)
				match panInterpolation:
					case '1':
						print ("UPDATE session SET pan1 = pan1 "+ (delta) +" WHERE id=1")
						panCursor.execute("UPDATE session SET pan1 = pan1 "+ (delta) +" WHERE id=1")
					case '2':
						panCursor.execute("UPDATE session SET pan2 = pan2 "+ (delta) +" WHERE id=1")
					case '4':
						panCursor.execute("UPDATE session SET pan4 = pan4 "+ (delta) +" WHERE id=1")
					case '8':
						panCursor.execute("UPDATE session SET pan8 = pan8 "+ (delta) +" WHERE id=1")
					case '16':
						panCursor.execute("UPDATE session SET pan16 = pan16 "+ (delta) +" WHERE id=1")
					case '32':
						panCursor.execute("UPDATE session SET pan32 = pan32 "+ (delta) +" WHERE id=1")
					case '64':
						panCursor.execute("UPDATE session SET pan64 = pan64 "+ (delta) +" WHERE id=1")
					case '128':
						panCursor.execute("UPDATE session SET pan128 = pan128 "+ (delta) +" WHERE id=1")
					case '256':
						panCursor.execute("UPDATE session SET pan256 = pan256 "+ (delta) +" WHERE id=1")
				
				
			
					
				#commit before sleeping so we release lock
				panConnection.commit()
				time.sleep(panSlewDelay)
		finally:
			#close open cursor and commit  
			panCursor.close()
			panConnection.commit()		
			print ("Finished pan thread")
		return
	

	
	def _slew_tilt_thread():
		try:
			print("Started tilt thread...")
			tiltConnection=sqlite3.connect("lunaves.db")
			tiltCursor = tiltConnection.cursor()	
			while (tiltMovementState == 'SLEWING'):
				step = 1
				tiltMotor.move(step, tiltDirection, tiltInterpolation)
				
				#if moving in current direction, just increment counter, else decrement
				result = tiltCursor.execute ("SELECT tiltDirection from SESSION where id=1")
				motorTiltDirection = result.fetchone()[0]
				if tiltDirection == motorTiltDirection :
					print("same tilt direction",tiltDirection, motorTiltDirection)
					delta = "+" + str(step)
				else:
					print("different tilt direction",tiltDirection, motorTiltDirection)
					delta = "-" + str(step)
				
				#update database here
					print ("TILT INTERPOLATION: ", tiltInterpolation)
				match tiltInterpolation:
					case '1':
						tiltCursor.execute("UPDATE session SET tilt1 = tilt1 "+ (delta) +" WHERE id=1")
					case '2':
						tiltCursor.execute("UPDATE session SET tilt2 = tilt2 "+ (delta) +" WHERE id=1")
					case '4':
						tiltCursor.execute("UPDATE session SET tilt4 = tilt4 "+ (delta) +" WHERE id=1")
					case '8':
						tiltCursor.execute("UPDATE session SET tilt8 = tilt8 "+ (delta) +" WHERE id=1")
					case '16':
						tiltCursor.execute("UPDATE session SET tilt16 = tilt16 "+ (delta) +" WHERE id=1")
					case '32':
						tiltCursor.execute("UPDATE session SET tilt32 = tilt32 "+ (delta) +" WHERE id=1")
					case '64':
						tiltCursor.execute("UPDATE session SET tilt64 = tilt64 "+ (delta) +" WHERE id=1")
					case '128':
						tiltCursor.execute("UPDATE session SET tilt128 = tilt128 "+ (delta) +" WHERE id=1")
					case '256':
						tiltCursor.execute("UPDATE session SET tilt256 = tilt256 "+ (delta) +" WHERE id=1")

				tiltConnection.commit()
				time.sleep(tiltSlewDelay)
				
		
		finally:
				#close open cursor and commit  
				tiltCursor.close()
				tiltConnection.commit()
				print ("Finished tilt thread")
		return
	 
	
	
	
	
	if panMotorState == 'INITIALISED' and tiltMotorState == 'INITIALISED' and activeSession() :	
		try:
			if request.method == 'POST':
				global panSlewDelay, panDirection, panInterpolation, tiltSlewDelay,tiltDirection, tiltInterpolation
				#initialise to 0 for first time; rest of times it is overwritten below
				panSlewDelay=0.1
				tiltSlewDelay=0.1
				data = request.get_json()
				
				oldPanSlewDelay = panSlewDelay
				oldTiltSlewDelay = tiltSlewDelay
				
				panSlewDelay = data.get('panDelay')
				panDirection = data.get('panDirection')
				panInterpolation = data.get('panInterpolation')
				tiltSlewDelay = data.get('tiltDelay')
				tiltDirection = data.get('tiltDirection')
				tiltInterpolation = data.get('tiltInterpolation')
				
				
				if panMovementState == 'STATIONARY' and tiltMovementState == 'STATIONARY' :	
				
				
					#there can be case that the sleeping slewing threads from prior slew have not detected STATIONARY state set in DELETE
					#Setting status to SLEWING will cause them to miss termination and hence to resume execution together with new threads
					#for now the best we can do is pause execution with a small buffer around the longest itw oudl take for threads to check
					time.sleep(max(oldTiltSlewDelay, oldPanSlewDelay)+1)
					
					panMovementState='SLEWING'
					tiltMovementState='SLEWING'

					tiltThread = threading.Thread(target=_slew_tilt_thread, daemon=True, args=[])
					tiltThread.start()
					
					
					panThread = threading.Thread(target=_slew_pan_thread, daemon=True, args=[])
					panThread.start()
					

				elif panMovementState == 'SLEWING' and tiltMovementState == 'SLEWING':	
					print("New slewing intstruction...but we are still slewing ")
					# just let the threads go on	
					# we have updated the values which will automatically be picked up in the threads
				elif panMovementState == 'GOTO' and tiltMovementState == 'GOTO' :	
					print("Goto")
					abort(403,'{"message":"Pantilt is not initialised"}')
					
				return "ok"
			
			elif request.method == 'DELETE':
				#this will automatically stop the threads
				panMovementState='STATIONARY'
				tiltMovementState='STATIONARY'
				return "ok"
			
			elif request.method == 'GET':
				return jsonify(
				{
				"panDelay": panSlewDelay,
				 "panDirection": panDirection,
				 "panInterpolation": panInterpolation,
				 "tiltDelay": tiltSlewDelay,
				 "tiltDirection": tiltDirection,
				 "tiltInterpolation": tiltInterpolation,
				 }
				)
			return "ok"
		finally:
				print("")
				#close open cursor and commit  
				

	else:
		print("Pantilt not initialised")
		abort(403,'{"message":"Pantilt is not initialised"}')

 
@app.route('/pantilt/goto', methods=['POST', 'DELETE', 'GET'])
def gotoMovement():
	#global netPanSteps, netPanDirection, netTiltSteps, netTiltDirection
	global panMotorState, tiltMotorState, panMovementState, tiltMovementState

    
	if request.method == 'POST':
		return "ok"
    
	elif request.method == 'DELETE':
		return "ok"
    
	elif request.method == 'GET':
		return jsonify(
		{"motor_state":"",
		"movement_state": "",
		"movement_slewrate": ""}
		)
	return "ok"



if __name__ == '__main__':
	
    app.run(host=path, port=5000, debug=True) 

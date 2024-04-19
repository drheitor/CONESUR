#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 21 11:39:23 2024

@author: heitor
"""


from astropy.io import fits
import os
import numpy as np
from scipy.io import readsav

from splice_ech import splice


import bezier



import warnings
warnings.filterwarnings('ignore')






#devoloper test, splice not as function







#calling the splice 

#*c-ech with wave solution 
spec='./data/goodech-Blue.fits'

#spec='./data/Reduced_red/spec.ech'


ech = fits.open(spec)
#running test just for red arm
#RED------------------
directory = 'Reduced_blue'

    
ech = fits.open(spec)
print('============================')

print('HEADER')
print('============================')
print(ech[0].header)
print('============================')



spec=ech[1].data['SPEC']
sig=ech[1].data['SIG']

cont=ech[1].data['CONT']
wave=ech[1].data['WAVE']
    
sig = sig * np.sqrt(cont)
    
sav_data = readsav('data/'+directory+'/harps_blue.ord_default.sav')
    
blzcoef = sav_data.blzcoef
col_range=sav_data.col_range



#original funciton and the way it should be called 
#def splice(ech, wave, spec, blaz, index, sig=None, ORDERS=None, COLRANGE=None,
                #  WEIGHTS=None, SCALING=None, ORDER_SCALES=None, DEBUG=None, YRANGE=None, WRANGE=None):
                    
#splice(ech[1], wave, spec, blzcoef, index=0, COLRANGE=list(col_range))


#defining the calling parameter 
ech=ech[1]
wave=wave[0]
spec=spec[0]
blaz=blzcoef
index=0

sig=None
ORDERS=None

COLRANGE=list(col_range)
WEIGHTS=None

SCALING=None
ORDER_SCALES=None
DEBUG=None
YRANGE=None
WRANGE=None



#begin of the Splice "function as a code to make it easy for debuging 



# Sanity check for 'SPEC'
if not 'SPEC' in ech.columns.names :
    print('Ilegitimate ech structure: must include SPEC tag')
    raise SystemExit

# Sanity check for 'WAVE'
if not 'WAVE' in ech.columns.names :
    print('splice_ech expects the wavelength solution to be included in the ech structure')
    raise SystemExit

# Sanity check for 'CONT' (blaze functions)
if not 'CONT' in ech.columns.names:
    print('splice_ech expects the blaze functions to be included in the ech structure as CONT')
    raise SystemExit

# Additional optional parameters

if sig is not None:
    print('Applying Sigma...')
    # Sanity check for 'SIG'
    if not 'SIG' in ech.columns.names :
        has_sig = 1 
else:
    has_sig = 0


# defining the number of orders to user and the length in pixel of these orders


npix = ech.data.dtype['SPEC'].shape[1]  # Order length in pixels
nord = ech.data.dtype['SPEC'].shape[0]  # Number of spectral orders

# TEST
#nord=26

print("Lenth of orders in the ech :" +str(npix))
print("Number of orders in the ech :" +str(nord))


# creating the weights 

weights = np.zeros((npix, nord)) + 1

if COLRANGE is not None:
    print('Applying Col Range...')
    sz = np.shape(COLRANGE)
    #check the shape of the COLRANGE must be two, the begining and the end of each order pixel
    if sz[1] != 2:
        print('COLRANGE should match the nstructure of a spectral order, infor on begin and end pixel')
        print('Help:\n', COLRANGE)
        raise SystemExit
    #check if the number of orders are correct
    if sz[0] != nord:
        print('COLRANGE should match the number of spectral orders')
        print('Help:\n', COLRANGE)
        raise SystemExit
    colr = COLRANGE
else:
    colr = np.zeros((2, nord), dtype=int)
    colr[0, :] = 0
    colr[1, :] = npix - 1





if ORDERS is not None:
    print('Applying Orders...')
    # If a subset of orders was specified
    # the [0] is to fix the format of the ech
    sp = ech.data['SPEC'][0][:, ORDERS]
    ww = ech.data['WAVE'][0][:, ORDERS]
    bb = ech.data['CONT'][0][:, ORDERS]

    if sig is not None:
        unc = ech.data['SIG'][0][:, ORDERS]

    # DOIT WHY DOING IT AGAIN?
    npix = len(sp[0, 0])  # Order length in pixels
    nord = len(sp[0, :])   # Number of spectral orders

    weights = np.zeros((npix, nord)) + 1

else:
    # the [0] is to fix the format of the ech
    sp = ech.data['SPEC'][0]
    ww = ech.data['WAVE'][0]

    if SCALING is not None:
        print('Applying Scailing...')
        #bb = ech.data['CONT'][0] > 1. #original in IDL
        bb = ech.data['CONT'][0]
        bb[bb<1]=1
        print('Scailing')
        

        for iord in range(nord):
            i0 = colr[0, iord]
            i1 = colr[1, iord]

            # Calculate scale
            scale = np.median(ech.data['SPEC'][0][iord][i0:i1]) / np.median(np.median(ech.data['CONT'][0][iord][i0:i1], axis=0), axis=0)

            bb[i0:i1, iord] = np.median(ech.data['CONT'][0][iord][i0:i1], axis=0) * scale
            sp[i0:i1, iord] = ech.data['SPEC'][0][iord][i0:i1]

    else:
        bb = ech.data['CONT'][0]
        bb[bb<1]=1

        for iord in range(nord):
        
            i0 = colr[iord][0]  # python way to say i0=[0,iord] whoch means in idl the first element (0) of the iorder (the row)
            i1 = colr[iord][1]
            #bb[i0:i1, iord] = np.median(ech.data['CONT'][i0:i1, iord], axis=0)

    if sig is not None:
        print('Applying sig...')
        unc = ech.data['SIG']


#sp == spec; bb == cont; unc== sig;

#================================================================================

print('Beginning the Splice lower orders')
order_scales = np.ones(nord)
order_overlap = -np.ones((6, nord))

# Find the order with the largest signal #OK
# DOIT check if it is right 
bb[bb<0.1]=0.1
dd=sp / (bb)


signal_orders = np.median(dd,axis=1)
signal_orders=list(signal_orders)

iord0=signal_orders.index(max(signal_orders))

#Sanity check the code works until here

beg1 = colr[iord0][0]
end1 = colr[iord0][1]

w1 = ww[iord0][beg1:end1]
s1 = sp[iord0][beg1:end1]
b1 = bb[iord0][beg1:end1]

if has_sig==1:
    sig1 = unc[iord0][beg1:end1]


print('Starting backwards loop')
if iord0 > 0:
    for iord in np.flip(np.linspace(0, iord0-1, num=iord0)): #start with the biggest signal order and goes n-1 n-2 ...
        iord=int(iord)    
        beg0 = beg1  # Shift current order to previous
        end0 = end1
        w0 = w1
        s0 = s1
        b0 = b1
        if has_sig:
            sig0 = sig1
        
        beg1 = colr[iord][0]  # New current order
        end1 = colr[iord][1]
        w1 = ww[iord][beg1:end1]
        s1 = sp[iord][beg1:end1]
        b1 = bb[iord][beg1:end1]
        if has_sig:
            sig1 = unc[iord0][beg1:end1]
            
            
        #Defining the overlap region in i0 and ni0 where i0 is an array of the index (pixels) and ni0 its length
        i0 = np.where((w0 >= np.min(w1)) & (w0 <= np.max(w1)))[0] # Overlap within the previous order 
        ni0=len(i0)                     # Overlap within the previous order 
        ii0 = np.arange(len(i0))
        
        
        #setting the WRANGE
        if WRANGE is not None :  # If exclusion regions are given, check the overlaps
            for iwrange in range(len(WRANGE)//2):
                iii0 = np.where((w0[i0[ii0]] < WRANGE[0, iwrange]) or (w0[i0[ii0]] > WRANGE[1, iwrange]))[0]
                if len(iii0) > 0:
                    ii0 = ii0[iii0]
                # DOIT check that sctructure =>  WRANGE[0, iwrange]
                else:
                    ni0 = 0
                    
                    
        #Overlap with the current order based in the same logic as above
        i1 = np.where((w1 >= np.min(w0)) & (w1 <= np.max(w0)))[0] 
        ni1=len(i1)                    
        ii1 = np.arange(len(i1))
         
         
        #setting the WRANGE
        if WRANGE is not None :  # If exclusion regions are given, check the overlaps
            for iwrange in range(len(WRANGE)//2):
                iii1 = np.where((w1[i1[ii1]] < WRANGE[0, iwrange]) or (w1[i1[ii1]] > WRANGE[1, iwrange]))[0]
                if len(iii1) > 0:
                    ii1 = ii1[iii1]
                 
                else:
                    ni1 = 0      
        if (ni0 > 0) and (ni1 > 0):
            print('We have overlaping orders')
            
            #tempS0=






#print('Beginning the Splice higher orders')































































#
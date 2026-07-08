"""
Structure engine v-final2 — swing decoupled from 2CR candles.
CL1/CH1 = the running SWING EXTREME of the leg (lowest low / highest high since
the leg began), NOT the 2CR candle's own low/high. The 2CR is the TRIGGER that
freezes the already-tracked swing.

Rules (user-locked):
  BULLISH: 2CR = 2 red (2nd closes below 1st low). CH1 = highest high of the leg
    tracked continuously, frozen at the 2CR. Tentative low tracked; BoS (1 close
    above CH1) freezes CL2 = lowest low since CH1. CHOCH_BEARISH = 2 closes below
    CL2. Dual-CHOCH: old A+ armed as counter-level.
  BEARISH: mirror. CL1 = lowest low of leg, frozen at 2CR (2 green). CH2 tracked;
    BoS (1 close below CL1) freezes CH2 = highest high since CL1. CHOCH_BULLISH =
    2 closes above CH2.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

@dataclass
class Candle:
    o: float; h: float; l: float; c: float; idx: int

def is_green(c): return c.c > c.o
def is_red(c):   return c.c < c.o

class StructureEngine:
    def __init__(self):
        self.direction=None
        # continuous leg swing trackers (run every candle)
        self.swing_high=None; self.swing_high_i=None
        self.swing_low=None;  self.swing_low_i=None
        # bullish confirmed
        self.ch1=None; self.ch1_i=None
        self.cl2=None; self.cl2_i=None
        self.tent_low=None; self.tent_low_i=None
        self.tjl3_high=None
        # bearish confirmed
        self.cl1=None; self.cl1_i=None
        self.ch2=None; self.ch2_i=None
        self.tent_high=None; self.tent_high_i=None
        self.tjl3_low=None
        self.choch_count=0
        self.events=[]

    def _log(self,k,i,**kw): self.events.append({"event":k,"index":i,**kw})

    def _reset_swings(self, c):
        self.swing_high=c.h; self.swing_high_i=c.idx
        self.swing_low=c.l;  self.swing_low_i=c.idx

    def process(self, candles):
        for i,c in enumerate(candles):
            c1=candles[i-1] if i>=1 else None
            prior=candles[i-2] if i>=2 else None

            # continuous swing tracking every candle
            if self.swing_high is None or c.h>self.swing_high:
                self.swing_high=c.h; self.swing_high_i=i
            if self.swing_low is None or c.l<self.swing_low:
                self.swing_low=c.l; self.swing_low_i=i

            if self.direction is None:
                if c1 and prior and is_green(prior) and is_red(c1) and is_red(c) and c.c<c1.l:
                    self.direction="bullish"
                    self.ch1=self.swing_high; self.ch1_i=self.swing_high_i   # leg swing high
                    self.tent_low=None; self.cl2=None
                    self._log("2CR_CH1",self.ch1_i,CH1=round(self.ch1,2))
                    self.swing_low=c.l; self.swing_low_i=i
                elif c1 and prior and is_red(prior) and is_green(c1) and is_green(c) and c.c>c1.h:
                    self.direction="bearish"
                    self.cl1=self.swing_low; self.cl1_i=self.swing_low_i     # leg swing low
                    self.tent_high=None; self.ch2=None
                    self._log("2CR_CL1",self.cl1_i,CL1=round(self.cl1,2))
                    self.swing_high=c.h; self.swing_high_i=i
                continue

            # ===== BULLISH =====
            if self.direction=="bullish":
                if self.ch1 is not None:
                    if self.tent_low is None or c.l<self.tent_low:
                        self.tent_low=c.l; self.tent_low_i=i
                # CHOCH bearish: 2 closes below frozen cl2
                if self.cl2 is not None and c.c<self.cl2:
                    self.choch_count+=1
                    if self.choch_count>=2:
                        old_aplus=self.ch1
                        self._log("CHOCH_BEARISH",i,broke_CL2=round(self.cl2,2),
                                  zones={"A+":self.ch1,"DT":self.cl2,"RBS":self.tjl3_high})
                        self.direction="bearish"; self.choch_count=0
                        self.ch2=old_aplus; self.ch2_i=self.ch1_i
                        self.ch1=None; self.tent_low=None; self.cl2=None; self.tjl3_high=None
                        self.cl1=None; self.tent_high=None; self.tjl3_low=None
                        self._reset_swings(c)
                        continue
                else:
                    self.choch_count=0
                # BoS up: 1 close above ch1 -> freeze cl2 = lowest low since ch1
                if self.ch1 is not None and c.c>self.ch1:
                    self.cl2=self.tent_low; self.cl2_i=self.tent_low_i
                    self._log("BOS_UP",i,broke_CH1=round(self.ch1,2),
                              confirmed_CL2=round(self.cl2,2),swing_idx=self.cl2_i)
                    self.ch1=None; self.tent_low=None
                    self.swing_high=c.h; self.swing_high_i=i
                # seek next 2CR -> new CH1 (uses leg swing high)
                if self.ch1 is None:
                    if c1 and prior and is_green(prior) and is_red(c1) and is_red(c) and c.c<c1.l:
                        self.ch1=self.swing_high; self.ch1_i=self.swing_high_i
                        self.tjl3_high=self.ch1; self.tent_low=None
                        self._log("2CR_CH1",self.ch1_i,CH1=round(self.ch1,2))
                        self.swing_low=c.l; self.swing_low_i=i

            # ===== BEARISH (mirror) =====
            elif self.direction=="bearish":
                if self.cl1 is not None:
                    if self.tent_high is None or c.h>self.tent_high:
                        self.tent_high=c.h; self.tent_high_i=i
                if self.ch2 is not None and c.c>self.ch2:
                    self.choch_count+=1
                    if self.choch_count>=2:
                        old_aplus=self.cl1
                        self._log("CHOCH_BULLISH",i,broke_CH2=round(self.ch2,2),
                                  zones={"A+":self.cl1,"DB":self.ch2,"SBR":self.tjl3_low})
                        self.direction="bullish"; self.choch_count=0
                        self.cl2=old_aplus; self.cl2_i=self.cl1_i
                        self.cl1=None; self.tent_high=None; self.ch2=None; self.tjl3_low=None
                        self.ch1=None; self.tent_low=None; self.tjl3_high=None
                        self._reset_swings(c)
                        continue
                else:
                    self.choch_count=0
                if self.cl1 is not None and c.c<self.cl1:
                    self.ch2=self.tent_high; self.ch2_i=self.tent_high_i
                    self._log("BOS_DOWN",i,broke_CL1=round(self.cl1,2),
                              confirmed_CH2=round(self.ch2,2),swing_idx=self.ch2_i)
                    self.cl1=None; self.tent_high=None
                    self.swing_low=c.l; self.swing_low_i=i
                if self.cl1 is None:
                    if c1 and prior and is_red(prior) and is_green(c1) and is_green(c) and c.c>c1.h:
                        self.cl1=self.swing_low; self.cl1_i=self.swing_low_i
                        self.tjl3_low=self.cl1; self.tent_high=None
                        self._log("2CR_CL1",self.cl1_i,CL1=round(self.cl1,2))
                        self.swing_high=c.h; self.swing_high_i=i
        return self.events

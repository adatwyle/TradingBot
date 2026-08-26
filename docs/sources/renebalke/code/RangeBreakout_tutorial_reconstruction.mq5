//+------------------------------------------------------------------+
//| RangeBreakout_tutorial_reconstruction.mq5                        |
//|                                                                  |
//| RECONSTRUCTION — pas le code distribué.                          |
//| Source : transcript "Range Breakout Expert Advisor Coding        |
//| Tutorial for MT5" (youtube 1Y6j8_9Hzgk, 2025-09-03), où René     |
//| Balke dicte ce code ligne par ligne. Reconstitué le 2026-08-17   |
//| pour docs/sources/renebalke/ — usage : analyse, pas production.  |
//|                                                                  |
//| ÉCARTS CONNUS avec la version distribuée v1.40 (.ex5 only) :     |
//|  1. v1.40 place des STOP ORDERS aux bords du range dès la fin    |
//|     du range (+ buffer optionnel en points) ; cette version      |
//|     tutoriel entre AU MARCHÉ au premier tick qui casse.          |
//|     Différence d'exécution réelle : le stop order est rempli au  |
//|     niveau du range (± slippage), l'entrée marché au tick de     |
//|     détection.                                                   |
//|  2. v1.40 : suppression des ordres non exécutés à une heure      |
//|     "delete" distincte de l'heure de clôture des positions.      |
//|  3. v1.40 : TP et SL chacun en 3 modes (off / factor×range /     |
//|     percent du prix / points), trailing stop + break-even stop,  |
//|     fréquence de trades (1 buy / 1 sell / 2 total, etc.),        |
//|     filtre de taille de range (min/max en points ET en %),       |
//|     4 modes de volume (fixe / managed / percent / money).        |
//|  4. ⚠️ Incertitude SL percent : transcript 01 dit que la base de |
//|     calcul est le range high/low ("I would just leave it as it   |
//|     is"), transcripts 05/06 disent "1% of the position open      |
//|     price". Les deux formulations coexistent chez l'auteur.      |
//|  5. Le range est calculé sur bougies M1 quel que soit le chart.  |
//+------------------------------------------------------------------+
#include <Trade/Trade.mqh>

// --- inputs (valeurs par défaut = celles du tutoriel : USDJPY 3h-6h)
input int RangeStartHour   = 3;
input int RangeStartMinute = 0;
input int RangeEndHour     = 6;
input int RangeEndMinute   = 0;
input int TradingEndHour   = 18;   // clôture forcée des positions
input int TradingEndMinute = 0;
input double RiskMoney     = 50;   // risque monétaire fixe par trade
input long  Magic          = 12345;

// --- globals
datetime rangeTimeStart, rangeTimeEnd, tradingTimeEnd;
double   rangeHigh = 0, rangeLow = 0;
bool     isTrade   = false;        // 1 trade max / jour (version tutoriel)
CTrade   trade;

int OnInit()
  {
   trade.SetExpertMagicNumber(Magic);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason) {}

void OnTick()
  {
   calculateTimes();
   calculateRange();

   // fenêtre de trading : après la fin du range, avant la clôture forcée
   if(TimeCurrent() > rangeTimeEnd && TimeCurrent() < tradingTimeEnd)
     {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(!isTrade && rangeHigh > 0 && rangeLow > 0)
        {
         if(bid > rangeHigh)                          // cassure haussière
           {
            trade.Buy(calculateLots(), _Symbol, 0, rangeLow);   // SL = bas du range
            isTrade = true;
           }
         else if(bid < rangeLow)                      // cassure baissière
           {
            trade.Sell(calculateLots(), _Symbol, 0, rangeHigh); // SL = haut du range
            isTrade = true;
           }
        }
     }

   // clôture forcée à l'heure de fin (pas de TP : la sortie EST l'heure)
   if(TimeCurrent() >= tradingTimeEnd)
     {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         CPositionInfo pos;
         if(pos.SelectByIndex(i) && pos.Magic() == Magic)
            trade.PositionClose(pos.Ticket());
        }
     }
  }

// borne les 3 horodatages au jour courant ; reset quotidien
void calculateTimes()
  {
   MqlDateTime dt;
   TimeCurrent(dt);
   dt.sec = 0;

   dt.hour = RangeStartHour;  dt.min = RangeStartMinute;
   datetime newStart = StructToTime(dt);
   if(newStart != rangeTimeStart)          // nouveau jour → reset
     {
      isTrade   = false;
      rangeHigh = 0;
      rangeLow  = 0;
     }
   rangeTimeStart = newStart;

   dt.hour = RangeEndHour;    dt.min = RangeEndMinute;
   rangeTimeEnd   = StructToTime(dt);

   dt.hour = TradingEndHour;  dt.min = TradingEndMinute;
   tradingTimeEnd = StructToTime(dt);
  }

// high/low des bougies M1 entre début et fin de range
void calculateRange()
  {
   double highs[], lows[];
   CopyHigh(_Symbol, PERIOD_M1, rangeTimeStart, rangeTimeEnd, highs);
   CopyLow (_Symbol, PERIOD_M1, rangeTimeStart, rangeTimeEnd, lows);
   if(ArraySize(highs) < 1 || ArraySize(lows) < 1) return;

   rangeHigh = highs[ArrayMaximum(highs)];
   rangeLow  = lows [ArrayMinimum(lows)];
   // (le tutoriel dessine aussi un rectangle OBJ_RECTANGLE — cosmétique, omis)
  }

// taille de lot pour risquer RiskMoney si le SL initial est touché
double calculateLots()
  {
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double rangeSize = rangeHigh - rangeLow;           // distance de risque
   double riskPerLot = rangeSize / tickSize * tickValue;
   double lots = NormalizeDouble(RiskMoney / riskPerLot, 2);
   return lots;   // hors commission/slippage — assumé par l'auteur
  }

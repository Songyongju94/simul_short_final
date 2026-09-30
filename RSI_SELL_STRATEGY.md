# TEST 19 RSI 매도 시뮬레이션

- 실행 설정: TEST_NO=19. SignalDetectorService에서 runSellRSIOperation(target_symbol=None)을 호출한다. 특정 종목만 보려면 target_symbol="1000BONKUSDT"로 지정한다. TEST 18의 인덱스 범위 설정과는 독립적으로 RSI 매수 기록 전체를 처리한다.
- 대상: candleBuyResultList의 buyMode=RSI_BB_15M, position=LONG. recentLow가 없거나 0인 과거 기록은 SKIPPED 로그를 남기며 임의의 저점을 만들지 않는다.
- 손절가: min(recentLow, BuyPrice × 0.95). 매수한 1분봉부터 완료된 1분봉 LOW가 손절선 이하이면 손절선 가격에 남은 수량 전부를 손절한다. 정확히 손절선에 닿아도 체결한다. 익절 전이면 최초 수량 100%, 이미 50% 익절했다면 나머지 50%를 청산한다. 시가가 손절선 아래로 갭 하락해도 요청한 시뮬레이션 가정에 따라 손절선 가격을 쓴다.
- 익절: 매 5분 경계의 시가가 매수가의 105% 이상이면 최초 수량의 50%를 매도한다. 이후 4시간 볼린저 상단을 초과하면 나머지 50%를 매도한다. 두 조건이 한 틱에 충족되면 같은 시각의 1차·2차 매도로 기록한다. 같은 분에서는 시가 익절을 먼저 평가하고 이후 LOW로 손절을 평가한다. 손절 후에는 잔량이 없으므로 추가 매도하지 않는다.
- 4시간 볼린저: UTC 00/04/08/12/16/20시 기준. 직전 확정 4시간봉 종가 19개와 현재 5분 시가 1개로 평균 + 모집단 표준편차 × 2를 계산한다. 현재 4시간봉의 미래 종가를 사용하지 않는다. 1분봉의 5분 경계 시가는 같은 시장의 5분봉 시가에 해당한다.
- 데이터: 기존 BinanceFuturesClient의 공개 과거 1분봉/4시간봉 조회를 사용한다. API 키나 주문 호출이 필요하지 않으며 candleList를 삭제/수정하지 않는다. TEST 18이 원본 캔들을 삭제했어도 실행할 수 있다. 1분봉을 최대 500개씩 조회하고 필요한 4시간봉을 캐시한다. 누락된 1분봉, 필요한 4시간봉 누락은 WAITING으로 해당 배치를 보류한다. API 오류는 진행 지점을 넘기지 않고 실행을 중단한다.
- 결과: 최초 매도 시 candleSellResultList에 한 행을 생성하고 2차 매도 시 같은 행을 갱신한다. buyUid = candleBuyResultList.uid로 매수와 연결한다. 매도가 아직 없으면 결과 행도 없으며 LEFT JOIN으로 미매도 매수 기록까지 확인할 수 있다. conditions=RSI19v3:<매수 uid>, 세부 사유는 sell1Reason/sell2Reason의 STOP / TP5 / BB4H다. 처음부터 전량 손절되면 1차 컬럼에 전량을 기록하고 2차 컬럼은 기본값으로 남긴다.
- 마지막에 추가되는 컬럼: buyUid, sell1Price, sell1Quantity, sell1Time, sell1TimeEpoch, sell1ProfitPrice, sell1Reason, sell2Price, sell2Quantity, sell2Time, sell2TimeEpoch, sell2ProfitPrice, sell2Reason. 1차·2차는 실행 순서다. Time은 KST 문자열, TimeEpoch는 epoch 초다. 미발생한 2차 매도의 숫자는 0, 시간/사유는 빈 문자열이다.
- 수량: SINGLE_BALANCE / 매수가를 최초 수량으로 계산한다. quantityOrg는 최초 수량, quantity는 1차+2차 매도 수량, sellPrice는 매도 수량 가중평균 가격, sellTime은 마지막 매도 시각이다. profitPrice = sell1ProfitPrice + sell2ProfitPrice이며 각 손익에는 기존 TRADING_FEE(퍼센트)를 매도 비중만큼 차감한다. 손실은 음수, 이익은 양수다. funding과 leverage는 적용하지 않는다. profitPercent는 가중평균 매도가의 가격 수익률, totalPrice는 해당 매수의 초기금액 + 누적 실현손익, totalProfitPercent는 초기금액 대비 누적 실현손익률이다. 전체 계좌 누적잔고가 아니다.
- 재시작: rsi_sell_progress 테이블을 자동 생성해 매수 uid별 다음 1분 시각, 잔여 비중, 부분 익절 여부 등을 저장한다. 매도 결과를 먼저 확정하고 진행 상태를 저장한다. 사이에 중단되면 같은 배치를 다시 계산하되 동일 매수 uid/단계의 결과를 중복 저장하지 않는다. 동시에 두 TEST 19 실행은 DB 세션 락으로 막는다. 기존 매수 가격/저점/금액/수수료가 바뀌면 체크포인트 불일치로 중단한다.
- runSellRSIOperation(end_time=epoch초)으로 종료 시각(미포함)을 지정할 수 있다. 기본은 실행 시점의 완료된 마지막 1분봉까지이며, 아직 매도되지 않은 수량은 OPEN으로 남겨 다음 실행에서 이어간다.
- 스키마 호환: 기존 64개 컬럼 순서는 유지하고 13개를 마지막에 추가한다. 기존 매도 로직의 64개 값 INSERT는 기본값을 자동으로 덧붙여 저장한다. 기존 컬럼만 갱신하는 UPDATE는 추가 컬럼을 덮어쓰지 않는다. 기존 비RSI 결과는 buyUid=0, 세부 컬럼 기본값으로 유지한다.
- 이전 분할 행 변환: TEST 19 시작 시 이전 RSI19v2:<매수 uid>:<사유> 행은 원본을 rsi_sell_split_archive에 보관한 뒤 한 행으로 합친다. 이는 저장 형식 변환이며 전략 재계산이 아니다. 현재 전략 상태 버전은 3이다. 버전 1·2 체크포인트는 손절 조건이 달라 이어서 사용하지 않으며 버전 불일치로 중단한다. 새 기준으로 재계산하려면 기존 TEST 19 결과와 진행 상태를 별도 보관/초기화해야 한다. 프로그램은 기존 결과를 자동 삭제하거나 새 전략으로 덮어쓰지 않는다.

매수와 매도 결과 조회:

```sql
SELECT b.uid AS buyUid, b.symbol, b.buyTimeKST, b.BuyPrice,
       s.sell1Price, s.sell1Quantity, s.sell1Time, s.sell1ProfitPrice, s.sell1Reason,
       s.sell2Price, s.sell2Quantity, s.sell2Time, s.sell2ProfitPrice, s.sell2Reason,
       s.profitPrice
FROM candleBuyResultList b
LEFT JOIN candleSellResultList s ON s.buyUid = b.uid
WHERE b.buyMode = 'RSI_BB_15M'
ORDER BY b.symbol, b.buyTime, b.uid;
```

실제 DB와 서비스는 개발 검증에서 실행하지 않는다. tests/test_rsi_sell_strategy.py는 가짜 데이터로 손절/익절 주기, 미래 가격 배제, 분할 매도, 재시작 중복 방지를 확인한다.

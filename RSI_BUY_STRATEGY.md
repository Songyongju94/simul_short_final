# TEST 18 RSI 매수 시뮬레이션

## 실행
- 기존 candleList의 5분봉을 사용합니다. CANDLE_INTERVAL=5, TEST_NO=18로 실행합니다.
- SPECIFIC_IDX_FROM/TO는 DB 종목 이름 정렬 기준이며 0이면 제한하지 않습니다.
- TEST_NO=19 사전 수집 및 candlelist_rsi_1m 테이블은 필요 없습니다.
  이전 수집 메서드와 TEST 19 실행 분기는 삭제되었습니다.
- 실제 주문 없이 candleBuyResultList에 LONG / buyMode='RSI_BB_15M' 결과를 저장합니다.

## 조건
1. 완료된 15분봉 종가 <= 일봉 볼린저 하단 * 0.97
2. 완료된 15분봉 Wilder RSI(14) <= 30
3. 대기 중 각 1분봉 시가를 현재 15분봉의 임시 종가로 보고, 임시 종가 > 해당 15분봉 시가
4. 그 임시 종가로 계산한 15분 RSI(14) > 직전 마감 15분봉 RSI(14)

1·2번은 마감된 15분봉에서 확인합니다. 이후 기본 60분 동안 매 1분봉 시가로 3·4번을 확인하며, 최초 충족한 그 1분봉 시가에 매수를 기록합니다. 확인 시 1·2번은 다시 요구하지 않습니다.
임시 RSI는 매번 직전 확정 RSI의 평균 상승폭·하락폭에서 독립적으로 계산합니다. 1분마다 확정 RSI를 누적 갱신하지 않으며, 직전 1분의 임시 RSI와 비교하지 않습니다. 15분봉이 마감된 후에만 그 종가로 확정 RSI를 갱신합니다.
대기 종료 시각의 1분 시가까지 포함합니다. 대기 중 1·2번 재충족으로 시간을 연장하지 않습니다. 만료 후에는 새로운 1·2번 충족으로 다시 대기에 들어갈 수 있습니다. 필요한 1분봉 또는 대기 중 확정 15분봉 이력이 누락되면 오류로 중단하고 체크포인트를 진행시키지 않습니다.
`runBuyRSIBuyOperation(..., wait_minutes=60)`의 분 단위 인자로 조정합니다. 120/180/240은 각각 2/3/4시간이며 양의 15분 배수만 허용합니다.

거래량은 읽거나 조건으로 사용하지 않습니다.
5분봉 3개로 15분봉을, UTC 기준 연속 288개로 일봉을 만듭니다.
판정에 사용한 마지막 5분봉의 candleTime에서 정확히 20일 전 봉이 없으면 해당 시점을 건너뜁니다.
판정 시점에 완료된 최근 연속 일봉 20개도 필요합니다.
일봉 볼린저는 종가 평균 ± 모집단 표준편차 2배입니다.
부분 일봉이나 누락된 봉을 보충하지 않으므로 20일 경과 후에도 데이터가 부족하면 매수하지 않습니다.
전체 레코드 수가 아니라 각 종목별 기간과 연속성이 기준입니다.
미래의 확정 종가를 현재 진입 판정에 사용하지 않습니다. 진행 중인 봉은 그 시점의 1분봉 시가만 임시 종가로 사용합니다.

## 진입 가격
매수 대기 중인 15분 구간의 1분봉을 Binance 공개 API로 묶어서 조회합니다. 시가만 시간순으로 사용하며, 미래 1분봉 가격은 현재 판단에 사용하지 않습니다.
예를 들어 12:00에 1·2번 신호가 확정되고 12:07 시가에서 처음 3·4번이 만족되면, buyTime은 12:07이고 BuyPrice는 그 1분봉 시가입니다. 12:15 마감을 기다리지 않습니다.
실제 틱 체결 대신 1분봉 시가를 사용하는 시뮬레이션이며 수수료/슬리피지는 반영하지 않습니다.
이 1분봉은 DB에 별도 저장하지 않습니다. 정확한 시각의 봉이 없으면 해당 종목의 처리를 멈추고 다음 실행에서 미완료 구간을 재시도합니다.
API 오류는 실행을 중단하며 앞서 커밋한 결과는 유지됩니다.
동일 종목/매수시간/전략의 기존 결과는 저장 전에 건너뜁니다. 정확한 신호 재현을 위해 재처리 구간에서는 1분봉 조회가 다시 필요할 수 있습니다.
동일 종목의 RSI_BB_15M 매수 기록 중 후보 매수 시각보다 앞선 마지막 매수로부터 기본 2시간 동안 추가 매수를 차단합니다. `cooldown_hours=2` 인자로 조정하며 0은 제한 해제입니다. 정확히 2시간이 지난 시점부터 허용하고, 미래 매수 기록은 현재 후보의 제한 기준으로 사용하지 않습니다.
제한 중 확인된 매수 후보는 저장 없이 건너뛰고 `BUY_COOLDOWN_SKIPPED` 로그를 남깁니다. 제한 종료 시각까지 주문을 예약하지 않으며, 이후 새 대기/확인 조건이 필요합니다. 저장된 매수 기록을 읽으므로 재시작과 날짜 경계에서도 제한이 유지됩니다. 기존 매수 기록을 소급 삭제하지 않습니다.
이전 거래량 필터 버전 결과도 같은 전략 이름이므로 재실행 시 유지됩니다.

## 중단 후 재개와 원본 정리
- 실행 시 `rsi_buy_progress` 테이블을 생성합니다. 종목별 다음 처리 시각(`nextTime`, epoch 밀리초)과 Wilder RSI 누적 상태를 저장합니다.
- UTC 하루 단위로 처리합니다. 매수 신호가 없는 구간도 완료 위치를 기록하며, 마지막 구간은 마감된 15분봉까지 처리합니다. 진입 1분봉이 아직 마감되지 않은 구간은 다음 실행으로 미룹니다.
- 첫 구간에서 필요한 이력을 읽은 뒤에는 신규 구간만 DB에서 조회합니다. 종목별 메모리 캐시에 최근 20일과 처리 중인 날짜의 검증된 5분봉·일봉을 보관하며, 새 데이터가 추가된 날짜만 일봉을 집계합니다. 15분봉도 이번 처리 구간만 집계합니다. 재시작 시 캐시는 남아 있는 DB 이력으로 다시 구성합니다.
- 캐시는 실행 중 이미 읽은 원본이 변경되지 않는 것을 전제로 합니다. 일별 체크포인트, 원본 삭제, 매수 커밋, API 조회와 대기 시간은 기존과 동일합니다.
- 저장 순서는 매수 결과 커밋 → 진행 위치·RSI 상태 커밋 → 원본 삭제입니다. 중간에 멈추면 마지막 완료 구간 이후부터 재개합니다. 미완료 하루 구간은 다시 검사하지만 이미 저장된 매수는 중복 생성하지 않습니다.
- 삭제 범위는 해당 종목의 `candleTime < weekStartUTC(nextTime) - 20 * DAY`입니다. 최근 20개 일봉과 진행 중인 날짜의 5분봉은 유지하고, 그 이전 데이터만 10,000행씩 삭제합니다. 다른 종목이나 매수 결과는 삭제하지 않습니다.
- 원본 정리 후에도 RSI를 처음부터 재계산하지 않고 누적 상태를 복원하므로 연속 실행과 같은 결과를 유지합니다. 처리 완료 종목은 새 데이터가 없으면 계산하지 않습니다.
- 대기 시작·만료 시각과 설정한 대기 시간도 진행 상태에 저장됩니다. 저장된 대기 시간과 다른 설정으로 재개하면 오류로 중단합니다. 시간별 비교 실험은 백업 원본과 분리된 진행 기록·결과를 사용해야 합니다.
- 새 진행 기록에는 `execution_mode=intraminute_open_v1`을 저장합니다. 이전 15분봉 마감 진입 방식의 체크포인트는 오류로 중단해 결과 혼합을 방지합니다. 새 방식 검증에는 백업 원본을 복원하고 별도 DB 또는 별도로 초기화한 RSI 진행 기록·매수 결과를 사용해야 합니다. 기존 기록은 자동 삭제하지 않습니다.
- 기존 매수 결과만 있고 진행 기록이 없는 첫 실행은 원본을 한 번 순회해 상태를 만듭니다. 기존 매수 행은 그대로 유지합니다.
- 이 정리는 RSI 매수 생성에 필요한 데이터만 남깁니다. 과거 매수의 매도·손익 계산이나 다른 전략에는 백업 원본을 사용해야 합니다.
- 원본 삭제 후 전략이나 처리 완료 데이터를 바꿔 처음부터 검증하려면 백업을 복원하고 진행 기록과 기존 결과도 별도로 정리해야 합니다. 진행 테이블만 지우면 삭제된 이력을 복구할 수 없습니다.
- DB 이름 잠금으로 이 코드의 동시 실행을 막습니다. 다른 프로그램에서 같은 원본/결과를 변경하는 작업까지 막지는 않습니다.

## 결과
`recentLow`와 `recentLowTime`은 BUY_READY(`WAIT_STARTED`)부터 BUY 시점까지의 최저가와 해당 1분봉 시작 시각(epoch 초)입니다. 테이블 마지막에 추가되며 기존 열 위치는 유지합니다. 동일 저점이 반복되면 최초 시각을 유지합니다.
완료된 1분봉의 LOW를 누적하고 현재 매수 판단 시각의 OPEN도 반영합니다. 현재 1분봉의 LOW는 그 분의 OPEN에서 매수 여부를 판단한 뒤에만 반영하므로, 매수 이후의 가격을 손절 기준에 포함하지 않습니다. 1분봉 데이터만으로 실제 저점 체결 초까지 알 수 없어 시간 정밀도는 1분입니다.
대기 중 저점은 체크포인트에 저장하고 매수 시 결과 행에 고정합니다. 저점 정보가 없는 이전 intraminute 대기 기록은 대기 시작부터 재개 시각까지의 완료된 1분봉을 다시 조회해 복원합니다. 다른 전략 및 기존 매수 행은 미계산 표시로 0을 사용하며, 0을 유효한 손절 가격으로 사용하면 안 됩니다. 기존 매수 행의 저점을 소급 추정하지 않습니다.
이번 추가는 손절 기준 데이터의 생성·저장·조회까지이며, 해당 가격 도달 시 매도하는 실행 로직은 별도입니다.
candleTime은 매수 판단 당시 진행 중인 15분봉 시작, buyTime/triggerTime은 조건을 처음 만족한 1분봉 시작 시각입니다.
결과 시간 단위는 epoch 초이며 원본 candleList는 밀리초입니다.
`bolHigh/bolLow`는 대기 진입 당시의 밴드입니다. `close/triggerPrice/BuyPrice`는 조건을 만족한 1분봉 시가, `rsi`는 당시 임시 15분 RSI, `previousRSI`는 직전 확정 15분 RSI입니다. `high/low`는 해당 15분 구간에서 진입 시점까지 관찰한 1분 시가의 최대/최소로, 마감 후의 전체 고가·저가를 미리 저장하지 않습니다.
미사용 숫자 열은 0, 문자 열은 빈 문자열입니다.
동일 전략을 여러 프로세스에서 동시에 실행하지 않습니다.

```sql
SELECT symbol, candleTime, BuyPrice, buyTime, triggerPrice, buyMode
FROM candleBuyResultList
WHERE buyMode = 'RSI_BB_15M'
ORDER BY buyTime, symbol;
```

## Weekly candle cleanup
Daily checkpoints and buy processing are unchanged. Cleanup runs once per symbol per simulated UTC week (Monday 00:00, KST Monday 09:00), using the checkpoint timestamp rather than the execution date. Only rows older than that week start minus 20 days are deleted. History retention can therefore reach nearly 27 days between cleanups.
`rsi_buy_progress.lastPruneWeek` is added automatically on startup and is persisted only after all deletion batches commit. The first run after migration performs one catch-up cleanup; restarts within the same completed week skip deletion. Interrupted cleanup retries safely. `deleted=0` can now also mean that weekly cleanup was skipped.

## Completed symbol cleanup
When the durable checkpoint reaches the source end captured at startup, all remaining source rows for that symbol before that end are deleted in committed batches. Buy results and progress are retained. Newer rows added after the captured end are not deleted. Interrupted final cleanup is retried on restart. Progress-only symbols remain in the sorted source list to preserve index positions when source rows disappear.
`RSI completed` means final cleanup succeeded. `RSI incomplete` or `RSI waiting` means the source still has an unprocessed tail or processing stopped before completion; weekly history cleanup remains in effect for those symbols. A partial 15-minute tail is preserved.
After full source deletion, extending that symbol with new candles requires restoring the historical candles needed for the 20-day indicators from backup. Final cleanup is intended for a fixed historical simulation dataset.

recentLowTime? VARCHAR(19)? ?????. ?? ?? epoch ? ?? ??? ? UTC+9 ???? ????, ?? ??? ?? ?? ???? ????. ??? ?????? ?? ?? ??? ?? epoch ??? ?????.

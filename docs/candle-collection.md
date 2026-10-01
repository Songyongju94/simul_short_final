# 캔들 수집 (TEST 1)

기존 `fetchCandle(interval)` → `backupCandleList()` 호출로 동작한다.
공유 메서드를 사용하는 TEST 0에도 같은 수집 방식이 적용된다.

- 기존 candleList를 비우지 않는다. 요청 기간의 월별 시각 목록을 조회하여
  앞부분·중간·마지막의 누락 구간을 모두 보충한다.
- 지정 종료 시각 및 현재 시각 전에 완성된 캔들만 저장한다.
- 월이 종료되었고 누락 캔들이 1,440개 이상이면 Binance USD-M 월별 ZIP을
  먼저 사용한다. SHA-256 CHECKSUM을 검증하며, 파일이 없거나 데이터가 부족하면
  해당 누락 구간을 REST API로 보충한다. 체크섬 불일치 및 HTTP 실패는 전파한다.
- HTTP 작업자는 최대 4개이고 세션은 작업자별로 분리한다. DB는 호출 스레드에서만
  접근하며 1,000행씩 저장하고 커밋한다. 저장 실패 배치는 롤백한다.
- REST 조회는 499개씩 요청한다. exchangeInfo의 분당 요청 가중치 한도의 절반을
  사용하며 서버 사용량 헤더와 429/418의 Retry-After를 공유 대기에 반영한다.
- BAD_SYMBOL은 종목명과 함께 기록하고 해당 실행에서 건너뛴다. 다른 오류나
  남아 있는 캔들 누락은 성공으로 처리하지 않는다. 재실행 시 저장된 행은 유지된다.
- 백업은 DB 내 임시 테이블에 완성한 후 RENAME TABLE로 교체한다. 기존 백업은
  복사 실패 시 유지된다. 수집 revision과 행 수/최대 uid가 같으면 복사를 생략한다.
  수집기 밖에서 OHLC를 직접 수정한 경우에는 revision도 갱신해야 생략되지 않는다.

첫 실행에서 `candle_collection_meta`와 `(symbol, candleTime)` UNIQUE 인덱스를
생성한다. 대용량 테이블의 최초 인덱스 생성에는 시간이 걸릴 수 있다. 기존 중복이
있으면 삭제하지 않고 오류로 알린다. 이후 봉 간격 변경은 같은 테이블에 섞지 않도록
거부한다. 메타데이터가 없는 기존 비어 있지 않은 테이블은 요청 대상인 5분봉으로
간주하므로, 기존 데이터가 다른 간격이면 별도 DB를 사용해야 한다.

로그는 `schemaReady`, 종목/월별 `httpSeconds`, `dbReadSeconds`, `dbWriteSeconds`,
전체 `elapsedSeconds`, 백업 `updated`와 소요 시간을 제공한다. HTTP 시간에는
다운로드·요청 대기·파싱이 포함되며, 병렬 작업들의 시간을 더한 값은 전체 경과 시간과
다르다. 실패 후 다시 실행하면 정상 커밋된 데이터부터 이어서 누락을 확인한다.

이 변경은 실제 DB나 API를 실행하지 않고 오프라인 HTTP/DB 대역으로 검증했다.

참고: [Binance 공개 파일](https://github.com/binance/binance-public-data),
[캔들 요청 가중치](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data).

.PHONY: server gateway tests demo

server:            ## core API (stdlib) على 9008
	python3 core/server.py --port 9008

gateway:           ## بناء وتشغيل بوابة Go على 9100
	cd gateway && gofmt -w . && go vet ./... && go build -o ../bin/meshai-gateway .
	./bin/meshai-gateway

tests:             ## فحوصات بلا شبكة
	python3 tests/test_meshai.py -v
	node --check telemetry/relay.js

demo:              ## ديمو حري عبر البوابة (الخادم الابتدائي)
	curl -s -X POST http://127.0.0.1:9100/submit -H "Content-Type: application/json" \
	  -d '{"prompt":"اكتب دالة f(xs) تعيد مجموع قائمة أعداد","test_harness":"assert f([1,2,3]) == 6"}'
	@echo "\n→ تتبع: http://127.0.0.1:9008/api/task/<id>"

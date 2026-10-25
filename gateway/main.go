// Aodı-MeshAI — gateway: بوابة موازية للأداء العالي (stdlib فقط).
// نقاط الاتصال:
//
//	GET  /health        الرمز الحي + uptime
//	POST /submit        استقبال مهمة {prompt,...} وإعادة توجيهها إلى core
//	GET  /stats         عدّادات + توزيع زمني
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

const (
	defaultCore = "http://127.0.0.1:9008"
	maxBody     = 4 << 20 // 4MB
)

var (
	startedAt = time.Now()
	coreURL   = getenv("MESH_CORE", defaultCore)
	reqCount  int64
	errCount  int64
	tasksOK   int64

	buckets [6]int64 // <50ms, <200, <1s, <5s, <30s, else
	bmu     sync.Mutex
)

func getenv(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, 200, map[string]any{
		"service":        "meshai.gateway",
		"version":        "1.0.0",
		"uptime_seconds": int(time.Since(startedAt).Seconds()),
		"core":           coreURL,
	})
}

func stats(w http.ResponseWriter, r *http.Request) {
	bmu.Lock()
	b := buckets
	bmu.Unlock()
	writeJSON(w, 200, map[string]any{
		"requests":       atomic.LoadInt64(&reqCount),
		"errors":         atomic.LoadInt64(&errCount),
		"tasks_accepted": atomic.LoadInt64(&tasksOK),
		"latency_ms": map[string]int64{
			"lt_50": b[0], "lt_200": b[1], "lt_1000": b[2],
			"lt_5000": b[3], "lt_30000": b[4], "gt_30000": b[5],
		},
	})
}

func submit(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeJSON(w, 405, map[string]string{"error": "POST مطلوب"})
		return
	}
	atomic.AddInt64(&reqCount, 1)
	start := time.Now()
	body, err := io.ReadAll(io.LimitReader(r.Body, maxBody))
	if err != nil {
		atomic.AddInt64(&errCount, 1)
		writeJSON(w, 400, map[string]string{"error": "قراءة الجسم فشلت"})
		return
	}
	req, err := http.NewRequest(http.MethodPost, coreURL+"/api/task", bytes.NewReader(body))
	if err != nil {
		atomic.AddInt64(&errCount, 1)
		writeJSON(w, 502, map[string]string{"error": "بناء الطلب فشل"})
		return
	}
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{Timeout: 15 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		atomic.AddInt64(&errCount, 1)
		writeJSON(w, 502, map[string]string{"error": "core لا يرد: " + err.Error()})
		return
	}
	defer resp.Body.Close()
	payload, _ := io.ReadAll(io.LimitReader(resp.Body, maxBody))
	lat := time.Since(start).Milliseconds()
	bmu.Lock()
	buckets[bucketIndex(lat)]++
	bmu.Unlock()
	if resp.StatusCode < 300 {
		atomic.AddInt64(&tasksOK, 1)
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("X-Gateway-Latency-Ms", strconv.FormatInt(lat, 10))
	w.WriteHeader(resp.StatusCode)
	_, _ = w.Write(payload)
}

func bucketIndex(ms int64) int {
	switch {
	case ms < 50:
		return 0
	case ms < 200:
		return 1
	case ms < 1000:
		return 2
	case ms < 5000:
		return 3
	case ms < 30000:
		return 4
	default:
		return 5
	}
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", health)
	mux.HandleFunc("/submit", submit)
	mux.HandleFunc("/stats", stats)
	addr := getenv("MESH_ADDR", ":9100")
	server := &http.Server{Addr: addr, Handler: mux,
		ReadHeaderTimeout: 5 * time.Second}
	fmt.Println("Aodı-MeshAI gateway v1.0.0 listening on", addr, "→ core:", coreURL)
	_ = server.ListenAndServe()
}

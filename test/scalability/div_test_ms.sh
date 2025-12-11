#!/bin/bash

BASE_URL="https://sirienergy.uab.cat"
COOKIE_FILE="cookies.txt"
REQUESTS=10000
CONCURRENCY=100

if [[ ! -f "$COOKIE_FILE" ]]; then
  echo "❌ Cookie file not found: $COOKIE_FILE"
  exit 1
fi

COOKIE_VALUE=$(cat "$COOKIE_FILE")
COOKIE_HEADER="user_data=${COOKIE_VALUE}"

mkdir -p results_div_ms

# Format: "METHOD URL JSON_FILE"
tests=(
  "GET $BASE_URL/processing/pvlibGen -"
  "GET $BASE_URL/weather -"
  "POST $BASE_URL/processing/surplus jsons/data_surplus.json"
)

# CSV file
CSV_FILE="results_div_ms/benchmark_results.csv"
if [[ ! -f "$CSV_FILE" ]]; then
  echo "Requests,Concurrency,time pvlibGen,time weather,time surplus" > "$CSV_FILE"
fi

# Arrays to store results
declare -A times

# Prepare folders
for test in "${tests[@]}"; do
  read method url json <<< "$test"
  name=$(basename "$url")
  mkdir -p "results_div_ms/result_${name}"
done

# Launch ALL tests concurrently
pids=()
for test in "${tests[@]}"; do
  read method url json <<< "$test"
  name=$(basename "$url")
  result_file="results_div_ms/result_${name}/result_n${REQUESTS}_c${CONCURRENCY}_${name}.txt"

  echo "🚀 Starting test: $method $url"

  if [[ "$method" == "POST" ]]; then
    ab -n "$REQUESTS" -c "$CONCURRENCY" \
      -p "$json" \
      -T application/json \
      -C "$COOKIE_HEADER" \
      "$url" > "$result_file" &
  else
    ab -n "$REQUESTS" -c "$CONCURRENCY" \
      -C "$COOKIE_HEADER" \
      "$url" > "$result_file" &
  fi

  pids+=($!)  # Track PID
done

# Wait for all to complete
wait "${pids[@]}"

echo "⏳ Reading results..."

# Parse results from files
for test in "${tests[@]}"; do
  read method url json <<< "$test"
  name=$(basename "$url")
  result_file="results_div_ms/result_${name}/result_n${REQUESTS}_c${CONCURRENCY}_${name}.txt"

  time_value=$(grep "Time per request:" "$result_file" | head -1 | awk '{print $4}')
  times[$name]=$time_value
  echo "  ✓ $name: ${time_value} ms"
done

# Append to CSV
echo "$REQUESTS,$CONCURRENCY,${times[pvlibGen]},${times[weather]},${times[surplus]}" >> "$CSV_FILE"

echo "🏁 All sequential tests completed"
echo "📊 Results appended to $CSV_FILE"

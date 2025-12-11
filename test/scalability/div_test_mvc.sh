#!/bin/bash

BASE_URL="https://sirienergy.uab.cat"
REQUESTS=10000
CONCURRENCY=100

mkdir -p results_div_mvc

# Format: "URL JSON_FILE"
tests=(
  "$BASE_URL/weather jsons/data_weather.json"
  "$BASE_URL/PVgen jsons/data_PVgen.json"
  "$BASE_URL/get_surplus_day jsons/data_get_surplus.json"
)

# CSV file
CSV_FILE="results_div_mvc/benchmark_results.csv"
if [[ ! -f "$CSV_FILE" ]]; then
  echo "Requests,Concurrency,time weather,time PVgen,time get_surplus_day" > "$CSV_FILE"
fi

# Arrays to store results
declare -A times

# Create folders
for test in "${tests[@]}"; do
  set -- $test
  url=$1
  name=$(basename "$url")
  mkdir -p "results_div_mvc/result_${name}"
done

# Run all tests concurrently
pids=()
for test in "${tests[@]}"; do
  set -- $test
  url=$1
  json=$2
  name=$(basename "$url")
  result_file="results_div_mvc/result_${name}/result_n${REQUESTS}_c${CONCURRENCY}_${name}.txt"

  echo "🚀 Starting test: POST $url"

  ab -n "$REQUESTS" -c "$CONCURRENCY" \
     -p "$json" \
     -T application/json \
     "$url" > "$result_file" &

  pids+=($!)
done

# Wait for all processes
wait "${pids[@]}"

echo "⏳ Reading results..."

# Parse "Time per request"
for test in "${tests[@]}"; do
  set -- $test
  url=$1
  name=$(basename "$url")
  result_file="results_div_mvc/result_${name}/result_n${REQUESTS}_c${CONCURRENCY}_${name}.txt"

  time_value=$(grep "Time per request:" "$result_file" | head -1 | awk '{print $4}')
  times[$name]=$time_value
  echo "  ✓ $name: ${time_value} ms"
done

# Append results to CSV
echo "$REQUESTS,$CONCURRENCY,${times[weather]},${times[PVgen]},${times[get_surplus_day]}" >> "$CSV_FILE"

echo "🏁 All concurrent MVC tests completed"
echo "📊 Results appended to $CSV_FILE"

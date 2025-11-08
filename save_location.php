<?php
// استقبال البيانات
$data = json_decode(file_get_contents("php://input"), true);

$lat = $data['latitude'] ?? '';
$lon = $data['longitude'] ?? '';
$date = date("Y-m-d H:i:s");

// حفظها في ملف نصي
$file = fopen("locations.txt", "a");
fwrite($file, "[$date] - Latitude: $lat, Longitude: $lon\n");
fclose($file);

// يمكن مشاهدة locations.txt مباشرة في VS Code بعد تشغيل السيرفر المحلي
echo "تم حفظ الموقع";
?>

$ErrorActionPreference='Stop'
$lab='C:\Users\User\Work\mink-lab'
$src='C:\Users\User\Work\mink-wt\integration'
$out="$lab\results\round10\integration-final\post-integration"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$tested='a67f671f4aa3a003751e3d06af85d2b9b8b459e5'
$head=(& git -C $src rev-parse HEAD).Trim()
$treeBefore=(& git -C $src rev-parse "${tested}:MinkowskiEngine").Trim()
$treeAfter=(& git -C $src rev-parse 'HEAD:MinkowskiEngine').Trim()
if($treeBefore -ne $treeAfter){throw 'Engine tree differs from certified runtime'}
$receipt=[ordered]@{source=$head;tested_runtime=$tested;engine_tree=$treeAfter;status='running';configurations=@()}
foreach($kind in @('cpu','cuda')) {
  $build="C:\Users\User\Work\mink-build\integration-$kind"
  $args=@('-NoProfile','-File',"$lab\tools\mink-build.ps1",'-Src',$src,'-Build',$build,'-Targets','help','-Who',"post-integrated-$kind")
  if($kind -eq 'cpu'){$args+='-Cpu'}
  & pwsh @args *> "$out\configure-$kind.log"
  if($LASTEXITCODE -ne 0){throw "$kind configure failed"}
  & C:\Users\User\Work\mink-env\cmake-4.2.3\bin\ctest.exe --test-dir $build -R '^(cmake_cpu_coordinate_manager_sources|adaptive_part_split_compare_tests)$' --verbose --output-junit "$out\ctest-$kind.xml" *> "$out\ctest-$kind.log"
  if($LASTEXITCODE -ne 0){throw "$kind new registry tests failed"}
  $bins=@('adaptive_tests','adaptive_split_tests','gaussian_tests','core_tests','ml_representations','point_dataset_tests','benchmark_memory_tests') | ForEach-Object { [ordered]@{name=$_;sha256=(Get-FileHash "$build\$_.exe").Hash} }
  $receipt.configurations += [ordered]@{kind=$kind;exit=0;binaries=$bins}
}
if((& git -C $src rev-parse HEAD).Trim() -ne $head -or (& git -C $src diff --name-only HEAD)){throw 'Source changed during post-integration checks'}
$receipt.status='passed';$receipt.completed=(Get-Date -Format o)
$receipt | ConvertTo-Json -Depth 9 | Set-Content "$out\receipt.json"
Write-Output "PASS: identical engine tree $treeAfter; new tests CPU2/2 CUDA1/1"

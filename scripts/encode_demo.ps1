param(
    [Parameter(Mandatory=$true)][string]$CaptureDirectory,
    [Parameter(Mandatory=$true)][string]$OutputFile
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$capture = (Resolve-Path -LiteralPath $CaptureDirectory).Path
$chapters = Get-Content -Raw -LiteralPath (Join-Path $root 'docs/media/narration.json') | ConvertFrom-Json
$voice = New-Object -ComObject SAPI.SpVoice
$voice.Rate = -2
$segments = foreach ($chapter in $chapters.PSObject.Properties) {
    $name = $chapter.Name
    $wave = Join-Path $capture "$name.wav"
    $audio = New-Object -ComObject SAPI.SpFileStream
    $audio.Open($wave, 3, $false)
    try {
        $voice.AudioOutputStream = $audio
        [void]$voice.Speak([string]$chapter.Value, 0)
    } finally {
        $audio.Close()
    }
    $segment = Join-Path $capture "$name.mp4"
    ffmpeg -nostdin -loglevel error -y -loop 1 -framerate 24 -i (Join-Path $capture "$name.jpg") -i $wave `
        -vf 'scale=1280:720' -af 'apad=pad_dur=0.75' -c:v libx264 -preset fast -tune stillimage -crf 22 `
        -pix_fmt yuv420p -c:a aac -b:a 80k -shortest $segment
    if ($LASTEXITCODE) { throw "Could not encode $name" }
    "file '$name.mp4'"
}

$manifest = Join-Path $capture 'concat.txt'
[IO.File]::WriteAllLines($manifest, [string[]]$segments, [Text.UTF8Encoding]::new($false))
$joined = Join-Path $capture 'walkthrough-native-speed.mp4'
ffmpeg -nostdin -loglevel error -y -f concat -safe 1 -i $manifest -c copy $joined
if ($LASTEXITCODE) { throw 'Could not assemble the walkthrough' }
$duration = [double]::Parse((ffprobe -v error -show_entries format=duration -of csv=p=0 $joined),
    [Globalization.CultureInfo]::InvariantCulture)
$speed = [Math]::Max(1.0, $duration / 86).ToString('0.000000', [Globalization.CultureInfo]::InvariantCulture)
ffmpeg -nostdin -loglevel error -y -i $joined -vf "setpts=PTS/$speed" -af "atempo=$speed" `
    -c:v libx264 -preset fast -crf 22 -c:a aac -b:a 80k -movflags +faststart $OutputFile
if ($LASTEXITCODE) { throw 'Could not write the final walkthrough' }

# 바탕 화면에 '손글씨 숫자 인식기' 바로가기를 만드는 스크립트
#
# 만들어지는 바로가기의 특징
#   - 프로젝트 venv 의 pythonw.exe 로 실행하므로 검은 콘솔 창이 뜨지 않는다.
#   - 아이콘은 손글씨인식.ico 로 지정된다.
#   - 작업 표시줄에 고정할 수 있다(바로가기를 마우스 오른쪽 클릭 → 작업 표시줄에 고정).
#
# 실행 방법
#   powershell -ExecutionPolicy Bypass -File 바로가기_만들기.ps1

$ErrorActionPreference = 'Stop'

# 이 스크립트가 있는 폴더를 프로젝트 폴더로 삼는다.
$프로젝트폴더 = Split-Path -Parent $MyInvocation.MyCommand.Path
$앱파일 = Join-Path $프로젝트폴더 'app.py'
$아이콘파일 = Join-Path $프로젝트폴더 '손글씨인식.ico'

# 1) 콘솔 없이 실행해 주는 pythonw.exe 를 찾는다.
#    venv 를 먼저 쓰고, 없을 때만 PATH 의 파이썬으로 넘어간다.
#    (패키지를 venv 에 설치하므로 venv 쪽을 기준으로 삼아야 바로가기가 그 패키지를 본다)
#    venv 는 저장소 루트에 있다. pyvenv.cfg 와 pip.exe 에 절대 경로가 박혀 있어
#    desktop_version 안으로 옮기면 깨지기 때문이다. 그래서 위쪽도 찾아본다.
$후보들 = @(
    (Join-Path $프로젝트폴더 'venv\Scripts\pythonw.exe'),
    (Join-Path (Split-Path -Parent $프로젝트폴더) 'venv\Scripts\pythonw.exe')
)
$파이썬w = $후보들 | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($파이썬w) {
    $환경설명 = '프로젝트 venv'
} else {
    Write-Output '※ venv 를 찾지 못해 PATH 의 파이썬을 사용합니다.'
    $파이썬 = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $파이썬) { throw '파이썬을 찾을 수 없습니다. venv 를 만들거나 python 을 PATH 에 넣으세요.' }
    $파이썬w = Join-Path (Split-Path -Parent $파이썬) 'pythonw.exe'
    if (-not (Test-Path $파이썬w)) { throw "pythonw.exe 를 찾을 수 없습니다: $파이썬w" }
    $환경설명 = '전역 파이썬'
}

# 앱이 필요로 하는 꾸러미가 그 환경에 있는지 미리 확인한다.
# (없는 채로 바로가기를 만들면 더블 클릭해도 창이 안 뜨고 원인도 안 보인다)
# pythonw.exe 는 창 없는 프로그램이라 파워셸이 종료를 기다리지 않는다.
# 그래서 확인은 같은 환경의 콘솔용 python.exe 로 해야 종료 코드를 제대로 받는다.
$검사용파이썬 = Join-Path (Split-Path -Parent $파이썬w) 'python.exe'
if (Test-Path $검사용파이썬) {
    $점검결과 = & $검사용파이썬 '-c' 'import torch, PIL, tkinter' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "$환경설명 에 필요한 꾸러미(torch, Pillow, tkinter)가 없습니다: $점검결과"
    }
    Write-Output "■ 꾸러미 확인 통과 (torch, Pillow, tkinter)"
}

# 2) 필요한 파일이 모두 있는지 확인한다.
foreach ($파일 in @($앱파일, $아이콘파일)) {
    if (-not (Test-Path $파일)) { throw "필요한 파일이 없습니다: $파일" }
}

# 3) 바탕 화면 경로를 구한다(원드라이브로 옮겨져 있어도 올바르게 찾는다).
$바탕화면 = [Environment]::GetFolderPath('Desktop')
$바로가기경로 = Join-Path $바탕화면 '손글씨 숫자 인식기.lnk'

# 4) 바로가기를 만든다.
$셸 = New-Object -ComObject WScript.Shell
$바로가기 = $셸.CreateShortcut($바로가기경로)
$바로가기.TargetPath = $파이썬w                      # 콘솔 없는 파이썬
$바로가기.Arguments = '"' + $앱파일 + '"'            # 실행할 프로그램
$바로가기.WorkingDirectory = $프로젝트폴더           # 가중치 파일을 찾을 기준 폴더
$바로가기.IconLocation = $아이콘파일 + ',0'          # 전용 아이콘
$바로가기.Description = '마우스로 쓴 숫자를 인식하는 PyTorch CNN 프로그램'
$바로가기.WindowStyle = 1                            # 보통 크기 창
$바로가기.Save()

# 5) 바로가기에 앱 이름(AppUserModelID)을 기록한다.
#    app.py 가 등록하는 값과 같아야 고정해 둔 아이콘과 실행 중인 창이 하나로 묶인다.
#    venv 로 실행하면 창을 띄우는 것은 기반 파이썬이라, 이 값이 없으면 둘이 따로 표시된다.
$앱ID = 'MnistHandwriting.Recognizer'
$앱ID설정됨 = $false
try {
    if (-not ('바로가기속성' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class 바로가기속성
{
    [ComImport, Guid("00021401-0000-0000-C000-000000000046")]
    private class 셸링크 { }

    [ComImport, Guid("0000010b-0000-0000-C000-000000000046"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IPersistFile
    {
        void GetClassID(out Guid pClassID);
        [PreserveSig] int IsDirty();
        void Load([MarshalAs(UnmanagedType.LPWStr)] string pszFileName, int dwMode);
        void Save([MarshalAs(UnmanagedType.LPWStr)] string pszFileName,
                  [MarshalAs(UnmanagedType.Bool)] bool fRemember);
        void SaveCompleted([MarshalAs(UnmanagedType.LPWStr)] string pszFileName);
        void GetCurFile([MarshalAs(UnmanagedType.LPWStr)] out string ppszFileName);
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct 속성키 { public Guid 서식id; public uint 번호; }

    [StructLayout(LayoutKind.Sequential)]
    private struct 속성값 { public ushort 형식; ushort 예약1, 예약2, 예약3; public IntPtr 값1; public IntPtr 값2; }

    [ComImport, Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IPropertyStore
    {
        void GetCount(out uint 개수);
        void GetAt(uint 순번, out 속성키 키);
        void GetValue(ref 속성키 키, out 속성값 값);
        void SetValue(ref 속성키 키, ref 속성값 값);
        void Commit();
    }

    // InitPropVariantFromString 은 헤더의 인라인 함수라 DLL 에서 불러올 수 없다.
    // 그래서 문자열용 PROPVARIANT(VT_LPWSTR)를 직접 만든다.
    private const ushort VT_LPWSTR = 31;

    [DllImport("ole32.dll", PreserveSig = false)]
    private static extern void PropVariantClear(ref 속성값 값);

    private static 속성값 문자열_속성값_만들기(string 문자열)
    {
        var 값 = new 속성값();
        값.형식 = VT_LPWSTR;
        값.값1 = Marshal.StringToCoTaskMemUni(문자열);   // PropVariantClear 가 해제한다
        return 값;
    }

    /// <summary>바로가기 파일에 AppUserModelID 를 기록한다.</summary>
    public static void 앱ID_설정(string 바로가기경로, string 앱ID)
    {
        var 링크 = (IPersistFile)new 셸링크();
        링크.Load(바로가기경로, 2);                     // 2 = 읽기/쓰기로 열기
        var 저장소 = (IPropertyStore)링크;
        // PKEY_AppUserModel_ID
        var 키 = new 속성키 {
            서식id = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 번호 = 5 };
        속성값 값 = 문자열_속성값_만들기(앱ID);
        try {
            저장소.SetValue(ref 키, ref 값);
            저장소.Commit();
        } finally {
            PropVariantClear(ref 값);
        }
        링크.Save(바로가기경로, true);
    }
}
'@
    }
    [바로가기속성]::앱ID_설정($바로가기경로, $앱ID)
    $앱ID설정됨 = $true
} catch {
    Write-Output "※ 앱 ID 기록 실패(고정은 되지만 실행 중 창이 따로 보일 수 있음): $($_.Exception.Message)"
}

Write-Output "■ 바로가기 생성 완료: $바로가기경로"
Write-Output "■ 실행 환경: $환경설명"
Write-Output "■ 실행 대상: $파이썬w"
Write-Output "■ 인수: $($바로가기.Arguments)"
if ($앱ID설정됨) { Write-Output "■ 앱 ID 기록: $앱ID" }
Write-Output '■ 작업 표시줄 고정: 바로가기를 마우스 오른쪽 클릭 → (추가 옵션 표시 →) 작업 표시줄에 고정'

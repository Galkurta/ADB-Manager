!include "MUI2.nsh"

; General
Name "ADB Manager"
OutFile "ADB-Manager-Setup.exe"
Unicode True
InstallDir "$PROGRAMFILES64\ADB Manager"
InstallDirRegKey HKCU "Software\ADB Manager" ""
RequestExecutionLevel admin

; Branding
BrandingText "ADB Manager Installer"

; Interface settings
!define MUI_ABORTWARNING
!define MUI_ICON "src\resources\icons\icon.ico"
!define MUI_UNICON "src\resources\icons\icon.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE" ; You might need to create this or remove if no license
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer Sections
Section "ADB Manager (required)" SecMain
    SectionIn RO
    
    SetOutPath "$INSTDIR"
    
    ; Copy files from dist folder
    File /r "dist\ADB-Manager\*"
    
    ; Store installation folder
    WriteRegStr HKCU "Software\ADB Manager" "" $INSTDIR
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Create Start Menu Shortcuts
    CreateDirectory "$SMPROGRAMS\ADB Manager"
    CreateShortcut "$SMPROGRAMS\ADB Manager\ADB Manager.lnk" "$INSTDIR\ADB-Manager.exe" "" "$INSTDIR\_internal\resources\icons\icon.ico"
    CreateShortcut "$SMPROGRAMS\ADB Manager\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    
    ; Create Desktop Shortcut
    CreateShortcut "$DESKTOP\ADB Manager.lnk" "$INSTDIR\ADB-Manager.exe" "" "$INSTDIR\_internal\resources\icons\icon.ico"
    
    ; Registry keys for Add/Remove programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ADBManager" "DisplayName" "ADB Manager"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ADBManager" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ADBManager" "DisplayIcon" "$INSTDIR\ADB-Manager.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ADBManager" "Publisher" "ADB Manager Team"
    
SectionEnd

; Uninstaller Section
Section "Uninstall"

    ; Remove files and directories
    RMDir /r "$INSTDIR"
    
    ; Remove shortcuts
    RMDir /r "$SMPROGRAMS\ADB Manager"
    Delete "$DESKTOP\ADB Manager.lnk"
    
    ; Remove registry keys
    DeleteRegKey HKCU "Software\ADB Manager"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ADBManager"

SectionEnd

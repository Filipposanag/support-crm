; NSIS Installer Script for Support CRM
; Professional installer with icons, license, and English interface
; Requires NSIS 3.11+
; Compile with: makensis build-nuitka\installer_nuitka.nsi

!define APP_NAME "Support CRM"
!define APP_VERSION "2.3.3"
!define COMPANY_NAME "PC-Project"
!define APP_PUBLISHER "Support"
!define APP_EXE "SupportCRM.exe"
!define INSTALL_DIR "$PROGRAMFILES\SupportCRM"
!define DATA_DIR "$PROGRAMDATA\SupportCRM"

; Modern UI
!include "MUI2.nsh"

; General Settings
Name "${APP_NAME}"
OutFile "..\dist\SupportCRM-Setup-${APP_VERSION}.exe"
InstallDir "${INSTALL_DIR}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel admin

; Compression
SetCompressor /SOLID lzma
SetCompressorDictSize 32

; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "..\Logo\favicon.ico"
!define MUI_UNICON "..\Logo\favicon.ico"

; Welcome page text
!define MUI_WELCOMEPAGE_TITLE "Welcome to ${APP_NAME} Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of ${APP_NAME}.$\r$\n$\r$\nIt is recommended that you close all other applications before starting Setup.$\r$\n$\r$\nClick Next to continue."

; Finish page options
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME}"
!define MUI_FINISHPAGE_LINK "Visit the ${APP_NAME} website"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller Pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages (English only for professional installer)
!insertmacro MUI_LANGUAGE "English"

; Version Information
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey "ProductName" "${APP_NAME}"
VIAddVersionKey "CompanyName" "${COMPANY_NAME}"
VIAddVersionKey "FileDescription" "${APP_NAME} Installer"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "LegalCopyright" "© ${COMPANY_NAME}"

; Global variable for config backup path
Var DB_CONFIG_BACKUP

; Installation Section
Section "!${APP_NAME}" SecMain
    SectionIn RO  ; Read-only, cannot be deselected
    
    ; ========== PRESERVE CONFIG BEFORE CLEAN ==========
    ; Backup db_config.json if it exists (preserve database connection settings)
    StrCpy $DB_CONFIG_BACKUP ""
    IfFileExists "$INSTDIR\config\db_config.json" 0 SkipBackup
        DetailPrint "Backing up database configuration..."
        CreateDirectory "$TEMP\SupportCRM_backup"
        CopyFiles /SILENT "$INSTDIR\config\db_config.json" "$TEMP\SupportCRM_backup\db_config.json"
        StrCpy $DB_CONFIG_BACKUP "$TEMP\SupportCRM_backup\db_config.json"
    SkipBackup:
    
    ; ========== CLEAN OLD INSTALLATION ==========
    ; Remove old program files to ensure clean update
    ; Data in ProgramData is preserved (license, backups, logs)
    IfFileExists "$INSTDIR\${APP_EXE}" 0 SkipClean
        DetailPrint "Cleaning old installation for fresh update..."
        ; Delete the entire installation directory
        RMDir /r "$INSTDIR"
    SkipClean:
    
    ; Create fresh installation directory
    CreateDirectory "$INSTDIR"
    SetOutPath "$INSTDIR"
    
    ; Copy all files and directories from build directory recursively
    File /r "..\dist\SupportCRM\SupportCRM\*"
    
    ; Create data directory for license, backups, logs
    CreateDirectory "${DATA_DIR}"
    CreateDirectory "${DATA_DIR}\backups"
    CreateDirectory "${DATA_DIR}\logs"
    
    ; ========== RESTORE CONFIG AFTER INSTALL ==========
    ; Restore db_config.json if it was backed up
    StrCmp $DB_CONFIG_BACKUP "" SkipRestore
        DetailPrint "Restoring database configuration..."
        CreateDirectory "$INSTDIR\config"
        CopyFiles /SILENT "$DB_CONFIG_BACKUP" "$INSTDIR\config\db_config.json"
        ; Clean up backup
        Delete "$DB_CONFIG_BACKUP"
        RMDir "$TEMP\SupportCRM_backup"
    SkipRestore:
    
    ; Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    
    ; Create Desktop shortcut
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Registry entries for Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "URLInfoAbout" "${APP_URL}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "HelpLink" "${APP_URL}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "EstimatedSize" 150000
    
    ; Store install directory for future reference
    WriteRegStr HKLM "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
    
SectionEnd

; Uninstaller Section
Section "Uninstall"
    ; Remove shortcuts
    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    
    ; Remove installation directory
    RMDir /r "$INSTDIR"
    
    ; Ask user if they want to keep data
    MessageBox MB_YESNO|MB_ICONQUESTION "Do you want to keep application data (license, backups, logs)?$\n$\nClick 'No' for complete removal." IDYES keep_data
    
    ; Remove data directory if user chose to delete
    RMDir /r "${DATA_DIR}"
    
    keep_data:
    
    ; Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKLM "Software\${APP_NAME}"
    
SectionEnd

; Section Descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "Core application files for ${APP_NAME}."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

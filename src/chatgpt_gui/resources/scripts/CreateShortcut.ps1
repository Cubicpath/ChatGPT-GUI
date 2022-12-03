###################################################################################################
#                              MIT Licence (C) 2022 Cubicpath@Github                              #
###################################################################################################

<#
    .SYNOPSIS
    Creates Desktop and Start Menu shortcuts.

    .DESCRIPTION
    This CreateShortcut.ps1 script creates shortcut (.lnk) files.
    This is implemented in PowerShell as accessing a WScript Shell is not convenient in Python.

    .PARAMETER Target
    Target of the shortcut.

    .PARAMETER Name
    Name of the shortcut.

    .PARAMETER Arguments
    Command line arguments to pass to the target.

    .PARAMETER Description
    Description of the shortcut.

    .PARAMETER Icon
    Path to an icon to use for the shortcut.

    .PARAMETER WorkingDirectory
    Working directory to start in when executing the shortcut.

    .PARAMETER Extension
    The file extension to use for shortcut files.
    ".lnk" and ".url" are the only extensions supprted by WScript.

    .PARAMETER Desktop
    Whether to create a desktop shortcut.

    .PARAMETER StartMenu
    Whether to create a start menu shortcut.

    .INPUTS
    None. You cannot pipe objects to CreateShortcut.ps1.

    .OUTPUTS
    System.Array. CreateShortcut.ps1 returns an array of strings containing a path to every shortcut created.

            -------------------------- EXAMPLE 1 --------------------------

            PS> CreateShortcut.ps1 "MyFile.exe" "My Shortcut"
            C:\Users\User\Desktop\My Shortcut.lnk
            C:\Users\User\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\My Shortcut.lnk

            -------------------------- EXAMPLE 2 --------------------------

            PS> CreateShortcut.ps1 -Target "MyFile.exe" -Name "My Shortcut" -Desktop $False
            C:\Users\User\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\My Shortcut.lnk

            -------------------------- EXAMPLE 3 --------------------------

            PS> CreateShortcut.ps1 "MyFile.exe" -Name "My Shortcut" -Desktop $False -StartMenu $False


    .LINK
    Repo: https://github.com/Cubicpath/ChatGPT-GUI

    .LINK
    Source: https://github.com/Cubicpath/ChatGPT-GUI/blob/master/src/chatgpt_gui/resources/scripts/CreateShortcut.ps1
#>


param(
    [Parameter(Mandatory)]
    [String]$Target,
    [Parameter(Mandatory)]
    [String]$Name,
    [String]$Arguments,
    [String]$Description,
    [String]$Icon,
    [String]$WorkingDirectory,
    [String]$Extension = '.lnk',
    [Boolean]$Desktop = $True,
    [Boolean]$StartMenu = $True
)


# Start creating shortcuts.
# If neither Desktop nor StartMenu are enabled, skip functionality.
if ( $Desktop -or $StartMenu) {
    $WshShell = New-Object -comObject WScript.Shell
    $FileName = $Name + $Extension


    Function Save-Shortcut($Path) {
        $Shortcut = $WshShell.CreateShortcut($Path)
        $Shortcut.TargetPath = $Target

        if ( $Arguments )        { $Shortcut.Arguments = $Arguments }
        if ( $Description )      { $Shortcut.Description = $Description }
        if ( $Icon )             { $Shortcut.IconLocation = $Icon }
        if ( $WorkingDirectory ) { $Shortcut.WorkingDirectory = $WorkingDirectory }

        $Shortcut.Save()
        Write-Output $Path
    }


    if ( $Desktop ) {
        $DesktopPath = [Environment]::GetFolderPath('Desktop')
        Save-Shortcut("$DesktopPath\$FileName")
    }

    if ( $StartMenu ) {
        $StartMenuPath = [Environment]::GetFolderPath('StartMenu')
        Save-Shortcut("$StartMenuPath\Programs\$FileName")
    }

}

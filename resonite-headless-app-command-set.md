# Command list for resonite headless app

## saveConfig

    Saves the current settings into the original config file
    Usage: saveconfig <filename> (optional, will save in place without)

## login

        Login to an account
        Usage: login <username/email> <password>

## logout

        Log out from the current account
        Usage: logout

## message

        Message user in friends list
        Usage: message <friend name> <message>

## invite

        Invite a friend to the currently focused world
        Usage: invite <friend name>

## friendRequests

        Lists all incoming friend requests
        Usage: friendrequests

## acceptFriendRequest

        Accepts a friend request
        Usage: acceptfriendrequest <friend name>

## worlds

        Lists all active worlds
        Usage: worlds

## focus

        Focus world
        Usage: focus <world name or number>

## startWorldURL

        Start a new world from URL
        Usage: startworldurl <record URL>

## startWorldTemplate

        Start a new world from template
        Usage: startworldtemplate <template name>

## status

        Shows the status of the current world
        Usage: status

## sessionUrl

        Prints the URL of the current session
        Usage: sessionurl

## sessionID

        Prints the ID of the current session
        Usage: sessionid

## copySessionURL

        Copies the URL of the current session to clipboard
        Usage: copysessionurl

## copySessionID

        Copies the ID of the current session to clipboard
        Usage: copysessionid

## users

        Lists all users in the world
        Usage: users

## close

        Closes the currently focused world
        Usage: close

## save

        Saves the currently focused world
        Usage: save

## restart

        Restarts the current world
        Usage: restart

## kick

        Kicks given user from the session
        Usage: kick <username>

## silence

        Silences given user in the session
        Usage: silence <username>

## unsilence

        Removes silence from given user in the session
        Usage: unsilence <username>

## ban

        Bans the user from all sessions hosted by this server
        Usage: ban <username>

## unban

        Removes ban for user with given username
        Usage: unban <username>

## listbans

        Lists all active bans
        Usage: listbans

## banByName

        Bans user with given username from all sessions hosted by this server
        Usage: banbyname <username>

## unbanByName

        Unbans user with the given username from all sessions hosted by this server
        Usage: unbanbyname <username>

## banByID

        Bans user with given User ID from all sessions hosted by this server
        Usage: banbyid <user ID>

## unbanByID

        Unbans user with given User ID from all sessions hosted by this server
        Usage: unbanbyid <user ID>

## respawn

        Respawns given user
        Usage: respawn <username>

## role

        Assigns a role to given user
        Usage: role <username> <role>

## name

        Sets a new world name
        Usage: name <new name>

## accessLevel

        Sets a new world access level
        Usage: accesslevel <access level name>

## hideFromListing

        Sets whether the session should be hidden from listing or not
        Usage: hidefromlisting <true/false>

## description

        Sets a new world description
        Usage: description <new description>

## maxUsers

        Sets user limit
        Usage: maxusers <max users>

## awayKickInterval

        Sets the away kick interval
        Usage: awaykickinterval <interval in minutes>

## import

        Import an asset into the focused world
        Usage: import <file path or URL>

## importMinecraft

        Import a Minecraft world. Requires Mineways to be installed.
        Usage: importminecraft <folder containing Minecraft world with the level.dat file>

## dynamicImpulse

        Sends a dynamic impulse with given tag to the scene root
        Usage: dynamicimpulse <tag>

## dynamicImpulseString

        Sends a dynamic impulse with given tag and string value to the scene root
        Usage: dynamicimpulsestring <tag> <value>

## dynamicImpulseInt

        Sends a dynamic impulse with given tag and integer value to the scene root
        Usage: dynamicimpulseint <tag> <value>

## dynamicImpulseFloat

        Sends a dynamic impulse with given tag and float value to the scene root
        Usage: dynamicimpulsefloat <tag> <value>

## spawn

        Spawns an item from a record URL into the world's root
        Usage: spawn <url> <active> <persistent>

## gc

        Forces full garbage collection
        Usage: gc

## debugWorldState

        Prints out diagnostic information for all worlds which can be used for debugging purposes
        Usage: debugworldstate

## shutdown

        Shuts down the headless client
        Usage: shutdown

## tickRate

        Sets the maximum simulation rate for the servers
        Usage: tickrate <ticks per second>

## log

        Switches the interactive shell to logging output. Press enter again to restore interactive.
        Usage: log

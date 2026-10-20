sub init()
    m.rows = m.top.findNode("rows")
    m.clock = m.top.findNode("clock")
    m.tick = m.top.findNode("tick")
    m.tick.observeField("fire", "updateClock")
    m.tick.control = "start"
    updateClock()

    m.rows.content = buildContent()
    m.rows.observeField("rowItemSelected", "onSelected")
    m.rows.setFocus(true)
end sub

' Rows of tiles. Each item is [label, color].
function buildContent() as object
    data = [
        { title: "Favourites", items: [["Movies", "0xEF4444FF"], ["Music", "0x8B5CF6FF"], ["Photos", "0x0EA5E9FF"], ["Live TV", "0x10B981FF"]] },
        { title: "Quick actions", items: [["Screensaver", "0x334155FF"], ["Theme", "0xFB923CFF"], ["About", "0x475569FF"]] }
    ]
    root = CreateObject("roSGNode", "ContentNode")
    for each r in data
        row = root.createChild("ContentNode")
        row.title = r.title
        for each it in r.items
            item = row.createChild("ContentNode")
            item.title = it[0]
            item.addFields({ tileColor: it[1] })
        end for
    end for
    return root
end function

sub updateClock()
    now = CreateObject("roDateTime")
    now.ToLocalTime()
    hours = Right("0" + now.GetHours().ToStr(), 2)
    minutes = Right("0" + now.GetMinutes().ToStr(), 2)
    m.clock.text = hours + ":" + minutes
end sub

sub onSelected()
    sel = m.rows.rowItemSelected
    item = m.rows.content.getChild(sel[0]).getChild(sel[1])
    ' print output shows up in the debug console: telnet <roku-ip> 8085
    print "Selected: "; item.title
end sub

function onKeyEvent(key as string, press as boolean) as boolean
    ' Return true to swallow a key. "back" returning false exits the channel.
    return false
end function

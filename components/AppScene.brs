' Feasibility screen: shows what this Roku and its display report about themselves.
sub init()
    info = CreateObject("roDeviceInfo")
    os = info.GetOSVersion()
    display = info.GetDisplayProperties()

    lines = [
        "Model: " + info.GetModelDisplayName() + " (" + info.GetModel() + ")"
        "Roku OS: " + os.major + "." + os.minor + "." + os.revision + " build " + os.build
        "Display: " + info.GetDisplayType() + ", video mode " + info.GetVideoMode() + ", UI " + info.GetUIResolution().name
        "HDR10: " + yesNo(display.Hdr10) + "   HDR10+: " + yesNo(display.Hdr10Plus) + "   HLG: " + yesNo(display.HLG) + "   Dolby Vision: " + yesNo(display.DolbyVision)
        "Decode H.264: " + canDecodeVideo(info, "mpeg4 avc") + "   HEVC: " + canDecodeVideo(info, "hevc") + "   VP9: " + canDecodeVideo(info, "vp9") + "   AV1: " + canDecodeVideo(info, "av1")
        "Decode AAC: " + canDecodeAudio(info, "aac") + "   AC-3: " + canDecodeAudio(info, "ac3") + "   E-AC-3: " + canDecodeAudio(info, "eac3")
    ]

    text = lines.Join(Chr(10))
    m.top.findNode("details").text = text
    print text
end sub

function canDecodeVideo(info as Object, codec as String) as String
    return yesNo(info.CanDecodeVideo({ Codec: codec }).result)
end function

function canDecodeAudio(info as Object, codec as String) as String
    return yesNo(info.CanDecodeAudio({ Codec: codec }).result)
end function

function yesNo(value as Dynamic) as String
    if type(value) <> "Boolean" and type(value) <> "roBoolean" then return "unknown"
    if value then return "yes"
    return "no"
end function

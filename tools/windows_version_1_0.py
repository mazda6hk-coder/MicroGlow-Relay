# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1, 0, 0, 0),
        prodvers=(1, 0, 0, 0),
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo([
            StringTable("040904B0", [
                StringStruct("CompanyName", "MicroGlow"),
                StringStruct("FileDescription", "MicroGlow Relay"),
                StringStruct("FileVersion", "1.0.0.0"),
                StringStruct("InternalName", "MicroGlow Relay"),
                StringStruct("OriginalFilename", "MicroGlow-Relay-1.0.exe"),
                StringStruct("ProductName", "MicroGlow Relay"),
                StringStruct("ProductVersion", "1.0.0.0"),
            ])
        ]),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

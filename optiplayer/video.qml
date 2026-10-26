import QtQuick
import QtMultimedia

Item {
    id: root
    property string fillModeName: "fit"

    VideoOutput {
        id: videoOut
        objectName: "videoOut"
        anchors.fill: parent
        fillMode: root.fillModeName === "fill" ? VideoOutput.PreserveAspectCrop
                : root.fillModeName === "stretch" ? VideoOutput.Stretch
                : VideoOutput.PreserveAspectFit
    }
}

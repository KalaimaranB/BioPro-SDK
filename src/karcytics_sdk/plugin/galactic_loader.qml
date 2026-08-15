import QtQuick 2.15

Rectangle {
    id: root
    width: 1000
    height: 700

    property string bgColor: "#0A0A0A"
    property string accentColor: "#00FF00"
    property string textColor: "#FFFFFF"
    property string moduleName: "Analysis Module"

    // Phase 2 status line — updated by Python's set_status_message()
    property string statusMessage: "STATUS: HYPERDRIVE ENGAGED"

    property real speed: 0.0
    property real targetSpeed: 0.05
    property real accel: 0.0004
    property int phase: 0
    property int warpOutTicks: 0
    property real globalOpacity: 0.0
    property real fadeSpeed: 0.02
    property string message: "Traveling to " + moduleName + "..."

    signal warpOutFinished()
    signal fadeOutFinished()

    NumberAnimation {
        id: fadeOutAnim
        target: root
        property: "opacity"
        from: 1.0
        to: 0.0
        duration: 500
        onStopped: root.fadeOutFinished()
    }

    function fadeOut(durationMs) {
        if (durationMs !== undefined && durationMs > 0) {
            fadeOutAnim.duration = durationMs
        }
        fadeOutAnim.start()
    }

    color: bgColor

    property var stars: []

    Component.onCompleted: {
        var newStars = []
        for (var i = 0; i < 300; i++) {
            newStars.push({
                x: (Math.random() * 3.0) - 1.5,
                y: (Math.random() * 2.0) - 1.0,
                z: (Math.random() * 1.9) + 0.1,
                size: (Math.random() * 1.5) + 1.0
            })
        }
        stars = newStars
    }

    function warpOut() {
        message = "ARRIVING AT DESTINATION..."
        warpOutTicks = 0
        phase = 1
    }

    function reset() {
        message = "Traveling to " + moduleName + "..."
        statusMessage = "STATUS: HYPERDRIVE ENGAGED"
        speed = 0.0
        globalOpacity = 0.0
        phase = 0
    }

    Timer {
        id: animTimer
        interval: 16
        running: true
        repeat: true
        onTriggered: {
            if (globalOpacity < 1.0) {
                globalOpacity = Math.min(1.0, globalOpacity + fadeSpeed)
            }

            if (phase === 0) {
                if (speed < targetSpeed) {
                    speed += accel
                }
            } else if (phase === 1) {
                speed += 0.02
                if (speed >= 0.8) {
                    speed = 0.8
                    warpOutTicks += 1
                    if (warpOutTicks >= 4) {
                        phase = 2
                        root.warpOutFinished()
                    }
                }
            }

            var s = stars;
            for (var i = 0; i < 300; i++) {
                s[i].z -= speed
                if (s[i].z <= 0.05) {
                    s[i].z = 2.0
                    s[i].x = (Math.random() * 3.0) - 1.5
                    s[i].y = (Math.random() * 2.0) - 1.0
                }
            }
            stars = s
            canvas.requestPaint()
        }
    }

    Canvas {
        id: canvas
        anchors.fill: parent
        opacity: globalOpacity

        onPaint: {
            var ctx = getContext("2d");
            var w = width;
            var h = height;
            var cx = w / 2;
            var cy = h / 2;

            ctx.clearRect(0, 0, w, h);

            var sArr = root.stars;
            for (var i = 0; i < 300; i++) {
                var s = sArr[i];
                var px = cx + (s.x * w) / s.z;
                var py = cy + (s.y * h) / s.z;

                var trailLength = speed * 15;
                var pzPrev = s.z + trailLength;
                var pxPrev = cx + (s.x * w) / pzPrev;
                var pyPrev = cy + (s.y * h) / pzPrev;

                var zFade = 1.0 - (s.z / 2.0);
                var alpha = Math.max(0, Math.min(1.0, zFade));

                if (speed > 0.025) {
                    ctx.strokeStyle = root.accentColor;
                    ctx.globalAlpha = alpha;
                } else {
                    ctx.strokeStyle = root.textColor;
                    ctx.globalAlpha = alpha;
                }

                var lw = Math.max(0.5, s.size * zFade * 0.8);
                ctx.lineWidth = lw;

                ctx.beginPath();
                if (speed > 0.005) {
                    ctx.moveTo(pxPrev, pyPrev);
                    ctx.lineTo(px, py);
                } else {
                    ctx.moveTo(px, py);
                    ctx.lineTo(px + lw, py);
                }
                ctx.stroke();
            }

            ctx.globalAlpha = 1.0;

            var grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(w, h) * 0.6);

            var r = 0, g = 0, b = 0;
            var hex = root.bgColor;
            if(hex.startsWith("#")) hex = hex.substring(1);
            if(hex.length === 6) {
                r = parseInt(hex.substring(0, 2), 16);
                g = parseInt(hex.substring(2, 4), 16);
                b = parseInt(hex.substring(4, 6), 16);
            }
            var luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            var aMid = (luma < 128) ? 0.15 : 0.08;
            var aEdge = (luma < 128) ? 0.8 : 0.4;

            grad.addColorStop(0, "rgba(" + r + "," + g + "," + b + ", 0)");
            grad.addColorStop(0.7, "rgba(" + r + "," + g + "," + b + ", " + aMid + ")");
            grad.addColorStop(1.0, "rgba(" + r + "," + g + "," + b + ", " + aEdge + ")");

            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, w, h);

            ctx.fillStyle = root.accentColor;
            ctx.font = "bold 28px 'Courier New'";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(root.message, cx, h * 0.75 + 30);

            ctx.globalAlpha = 0.5;
            ctx.fillStyle = root.textColor;
            ctx.font = "12px 'Courier New'";
            ctx.fillText(root.statusMessage, cx, h * 0.75 + 75);

            ctx.globalAlpha = 1.0;
        }
    }
}

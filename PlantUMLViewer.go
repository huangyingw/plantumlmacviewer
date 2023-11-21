package main

import (
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/canvas"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/storage"
	"fyne.io/fyne/v2/widget"
	"log"
	"os/exec"
	"path/filepath"
)

func main() {
	myApp := app.New()
	myWindow := myApp.NewWindow("PlantUML Viewer")

	image := canvas.NewImageFromFile("")
	image.FillMode = canvas.ImageFillContain // 可根据需要调整填充模式

	openFileButton := widget.NewButton("Open .puml File", func() {
		dialog.ShowFileOpen(func(file storage.URIReadCloser, err error) {
			if err != nil {
				log.Println("Failed to open file:", err)
				return
			}
			if file == nil {
				log.Println("No file chosen")
				return
			}
			go processFile(file.URI().Path(), image)
		}, myWindow)
	})

	myWindow.SetContent(container.NewVBox(
		image,
		openFileButton,
	))

	myWindow.ShowAndRun()
}

func processFile(filePath string, image *canvas.Image) {
	// 假设 PlantUML jar 文件位于 "/path/to/plantuml.jar"
	plantumlJarPath := "/path/to/plantuml.jar"
	pngFilePath := filepath.Dir(filePath) + string(filepath.Separator) +
		filepath.Base(filePath) + ".png"

	// 构建并运行 PlantUML 命令
	cmd := exec.Command("java", "-jar", plantumlJarPath, "-tpng", filePath, "-o", pngFilePath)
	err := cmd.Run()
	if err != nil {
		log.Println("Failed to execute PlantUML:", err)
		return
	}

	// 更新图像
	image.File = pngFilePath
	image.Refresh()
}

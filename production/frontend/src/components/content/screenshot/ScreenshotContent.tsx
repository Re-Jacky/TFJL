import React, { useState, useEffect } from 'react';
import { Button, Image, Spin, message, Empty, Select, Modal } from 'antd';
import { useAppSelector } from '@src/store/store';
import { selectActiveWindow } from '@src/store/selectors';
import { api } from '@src/services/api';
import styles from './ScreenshotContent.module.scss';
import ImageBrowser from './components/ImageBrowser';
import CropEditor from './components/CropEditor';
import CropLabeler from './components/CropLabeler';
import type { CropBox } from '@src/services/api';

const defaultCropBox = [
  { x: 410, y: 518, w: 66, h: 90 },
  { x: 495, y: 518, w: 66, h: 90 },
  { x: 580, y: 518, w: 66, h: 90 },
];

const ScreenshotContent: React.FC = () => {
  const activeWindow = useAppSelector(selectActiveWindow);
  const [loading, setLoading] = useState(false);
  const [detectionResult, setDetectionResult] = useState<any>(null);
  const [detectingCards, setDetectingCards] = useState(false);
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [unlabeledCrops, setUnlabeledCrops] = useState<any[]>([]);
  const [showUnlabeled, setShowUnlabeled] = useState(false);
  const [cardNames, setCardNames] = useState<string[]>([]);
  const [cropEditor, setCropEditor] = useState<{
    visible: boolean;
    crop: any;
    margins: { top: number; bottom: number; left: number; right: number };
    imageSize: { width: number; height: number };
    dragging: 'top' | 'bottom' | 'left' | 'right' | null;
    dragStart: { x: number; y: number } | null;
  } | null>(null);

  // Screenshot folder browsing
  const [screenshotFiles, setScreenshotFiles] = useState<string[]>([]);
  const [selectedFileIndex, setSelectedFileIndex] = useState<number>(0);
  const [currentImageUrl, setCurrentImageUrl] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<{
    width: number;
    height: number;
  } | null>(null);

  // Cropping workflow
  const [cropMode, setCropMode] = useState<'browse' | 'cropping' | 'labeling'>(
    'browse'
  );
  const [cropBoxes, setCropBoxes] = useState<CropBox[]>(defaultCropBox);
  const [extractedCrops, setExtractedCrops] = useState<string[]>([]);
  const [cropLabels, setCropLabels] = useState<string[]>(['', '', '']);
  const [savingLabels, setSavingLabels] = useState(false);

  // Load card names on mount
  useEffect(() => {
    const loadCardNames = async () => {
      try {
        const result = await api.getCardNames();
        setCardNames(result.cards || []);
      } catch (error) {
        console.error('Failed to load card names:', error);
        message.error('加载卡牌名称失败');
      }
    };
    loadCardNames();
  }, []);

  // Load model status on mount
  useEffect(() => {
    const loadModelStatus = async () => {
      try {
        const status = await api.getModelStatus();
        setModelStatus(status);
      } catch (error) {
        // Model not trained yet, ignore
      }
    };
    loadModelStatus();
  }, []);

  // Load screenshot files on mount
  useEffect(() => {
    loadScreenshotFiles();
  }, []);

  const loadScreenshotFiles = async () => {
    try {
      const result = await api.listScreenshots();
      setScreenshotFiles(result.files);
      if (result.files.length > 0) {
        setSelectedFileIndex(0);
        await loadScreenshotImage(result.files[0]);
      }
    } catch (error) {
      console.error('Failed to load screenshot files:', error);
      message.error('加载截图列表失败');
    }
  };

  const loadScreenshotImage = async (filename: string) => {
    try {
      setLoading(true);
      const result = await api.getScreenshotFile(filename);
      setCurrentImageUrl(result.image);
      setImageSize(result.size);
    } catch (error) {
      console.error('Failed to load screenshot:', error);
      message.error('加载截图失败: ' + error);
    } finally {
      setLoading(false);
    }
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle if in browse mode and not typing in input
      if (cropMode !== 'browse') return;
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      )
        return;

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handlePrevious();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleNext();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [cropMode, selectedFileIndex, screenshotFiles]);

  const handleSelectFile = async (index: number) => {
    setSelectedFileIndex(index);
    await loadScreenshotImage(screenshotFiles[index]);
    // Reset crop mode when switching images
    setCropMode('browse');
    setExtractedCrops([]);
    setCropLabels(['', '', '']);
  };

  const handlePrevious = () => {
    if (selectedFileIndex > 0) {
      handleSelectFile(selectedFileIndex - 1);
    }
  };

  const handleNext = () => {
    if (selectedFileIndex < screenshotFiles.length - 1) {
      handleSelectFile(selectedFileIndex + 1);
    }
  };

  const handleStartLabeling = () => {
    setCropMode('cropping');
    // Reset boxes to default positions
    setCropBoxes(defaultCropBox);
  };

  const handleFinishCropping = async () => {
    if (!screenshotFiles[selectedFileIndex]) {
      message.error('未选择截图');
      return;
    }

    try {
      setLoading(true);
      const result = await api.extractCrops(
        screenshotFiles[selectedFileIndex],
        cropBoxes
      );
      setExtractedCrops(result.crops);
      setCropLabels(['', '', '']);
      setCropMode('labeling');
      message.success('裁切完成，请标注卡牌');
    } catch (error) {
      console.error('Failed to extract crops:', error);
      message.error('裁切失败: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveLabels = async () => {
    if (!screenshotFiles[selectedFileIndex]) {
      message.error('未选择截图');
      return;
    }

    if (cropLabels.some((label) => !label.trim())) {
      message.warning('请为所有卡牌选择标签');
      return;
    }

    try {
      setSavingLabels(true);
      const cropsWithLabels = cropBoxes.map((box, idx) => ({
        ...box,
        label: cropLabels[idx],
      }));

      const result = await api.saveLabeledCrops({
        filename: screenshotFiles[selectedFileIndex],
        crops: cropsWithLabels,
      });

      message.success(result.message);

      // Refresh model status
      const status = await api.getModelStatus();
      setModelStatus(status);

      // Reset to browse mode
      setCropMode('browse');
      setExtractedCrops([]);
      setCropLabels(['', '', '']);
    } catch (error) {
      console.error('Failed to save labels:', error);
      message.error('保存标注失败: ' + error);
    } finally {
      setSavingLabels(false);
    }
  };

  const handleCancelLabeling = () => {
    setCropMode('browse');
    setExtractedCrops([]);
    setCropLabels(['', '', '']);
  };

  const handleCapture = async () => {
    if (!activeWindow) {
      message.error('请先选择一个游戏窗口');
      return;
    }

    setLoading(true);
    try {
      const pid = parseInt(activeWindow, 10);
      const result = await api.captureScreenshot(pid);
      if (result.success) {
        message.success('截图已保存到文件夹');

        // Reload file list
        await loadScreenshotFiles();

        // Auto-select the newly captured file
        const newIndex = screenshotFiles.findIndex(
          (f) => f === result.filename
        );
        if (newIndex !== -1) {
          await handleSelectFile(newIndex);
        } else {
          // If not found, it's the newest (index 0)
          await handleSelectFile(0);
        }
      } else {
        message.error(result.message || '截图失败');
      }
    } catch (error) {
      console.error('Screenshot error:', error);
      message.error('截图发生错误');
    } finally {
      setLoading(false);
    }
  };

  const handleDetectCards = async () => {
    // Prefer current screenshot file over active window
    const currentFile =
      screenshotFiles.length > 0 ? screenshotFiles[selectedFileIndex] : null;

    if (!currentFile && !activeWindow) {
      message.error('请先捕获截图或选择活动窗口');
      return;
    }

    setDetectingCards(true);
    try {
      let result;
      if (currentFile) {
        // Detect from current screenshot file
        result = await api.detectCards(undefined, currentFile);
      } else {
        // Fallback to active window
        result = await api.detectCards(parseInt(activeWindow!));
      }
      setDetectionResult(result);
      message.success('卡牌识别完成');
    } catch (error) {
      message.error('识别失败: ' + error);
    } finally {
      setDetectingCards(false);
    }
  };

  const handleLabelCard = async (cropId: string, cardName: string) => {
    try {
      const result = await api.labelCrop(cropId, cardName);
      message.success(result.message);
      // Refresh detection to show updated results
      handleDetectCards();
      // Refresh model status
      const status = await api.getModelStatus();
      setModelStatus(status);
    } catch (error) {
      message.error('标注失败: ' + error);
    }
  };

  const handleTrainModel = async () => {
    try {
      const result = await api.trainModel();
      message.success(`模型训练完成: ${result.train_samples} 样本`);
      const status = await api.getModelStatus();
      setModelStatus(status);
    } catch (error) {
      message.error('训练失败: ' + error);
    }
  };

  const handleBatchTrain = async () => {
    setLoading(true);
    try {
      const result = await api.batchTrainFromScreenshots();
      message.success(result.message);
      // Refresh detection and model status
      const status = await api.getModelStatus();
      setModelStatus(status);
    } catch (error) {
      message.error('批量训练失败: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchUnlabeled = async () => {
    setLoading(true);
    try {
      const result = await api.getUnlabeledCrops();
      // Convert base64 to data URLs for display
      const cropsWithUrls = (result.crops || []).map((crop) => ({
        ...crop,
        image_url: `data:image/png;base64,${crop.image_base64}`,
      }));
      setUnlabeledCrops(cropsWithUrls);
      setShowUnlabeled(true);
      message.success(`获取到 ${result.crops?.length || 0} 个未标注卡牌`);
    } catch (error) {
      message.error('获取未标注卡牌失败: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const handleLabelUnlabeledCard = async (cropId: string, cardName: string) => {
    try {
      // Get crop from state to check if it has margins
      const crop = unlabeledCrops.find((c) => c.crop_id === cropId);
      const cropMargins = crop?.crop_margins;

      const result = await api.labelCrop(cropId, cardName, cropMargins);
      message.success(result.message);
      // Remove from unlabeled list
      setUnlabeledCrops((prev) =>
        prev.filter((crop) => crop.crop_id !== cropId)
      );
      // Refresh model status
      const status = await api.getModelStatus();
      setModelStatus(status);
    } catch (error) {
      message.error('标注失败: ' + error);
    }
  };

  const handleOpenCropEditor = (crop: any) => {
    // Create temporary image to get dimensions
    const img = new window.Image();
    img.onload = () => {
      setCropEditor({
        visible: true,
        crop,
        margins: { top: 0, bottom: 0, left: 0, right: 0 },
        imageSize: { width: img.width, height: img.height },
        dragging: null,
        dragStart: null,
      });
    };
    img.src = crop.image_url;
  };

  const handleBorderMouseDown = (
    edge: 'top' | 'bottom' | 'left' | 'right',
    e: React.MouseEvent
  ) => {
    e.preventDefault();
    if (!cropEditor) return;
    setCropEditor({
      ...cropEditor,
      dragging: edge,
      dragStart: { x: e.clientX, y: e.clientY },
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!cropEditor || !cropEditor.dragging || !cropEditor.dragStart) return;

    const deltaX = e.clientX - cropEditor.dragStart.x;
    const deltaY = e.clientY - cropEditor.dragStart.y;

    // Get the displayed image element to calculate scale factor
    const imgElement = document.querySelector(
      '#cropEditorImage'
    ) as HTMLImageElement;
    if (!imgElement) return;

    const displayWidth = imgElement.width;
    const displayHeight = imgElement.height;
    const scaleX = cropEditor.imageSize.width / displayWidth;
    const scaleY = cropEditor.imageSize.height / displayHeight;

    const newMargins = { ...cropEditor.margins };

    switch (cropEditor.dragging) {
      case 'top':
        newMargins.top = Math.max(
          0,
          Math.min(
            cropEditor.imageSize.height - cropEditor.margins.bottom - 10,
            cropEditor.margins.top + Math.round(deltaY * scaleY)
          )
        );
        break;
      case 'bottom':
        newMargins.bottom = Math.max(
          0,
          Math.min(
            cropEditor.imageSize.height - cropEditor.margins.top - 10,
            cropEditor.margins.bottom - Math.round(deltaY * scaleY)
          )
        );
        break;
      case 'left':
        newMargins.left = Math.max(
          0,
          Math.min(
            cropEditor.imageSize.width - cropEditor.margins.right - 10,
            cropEditor.margins.left + Math.round(deltaX * scaleX)
          )
        );
        break;
      case 'right':
        newMargins.right = Math.max(
          0,
          Math.min(
            cropEditor.imageSize.width - cropEditor.margins.left - 10,
            cropEditor.margins.right - Math.round(deltaX * scaleX)
          )
        );
        break;
    }

    setCropEditor({
      ...cropEditor,
      margins: newMargins,
      dragStart: { x: e.clientX, y: e.clientY },
    });
  };

  const handleMouseUp = () => {
    if (!cropEditor) return;
    setCropEditor({
      ...cropEditor,
      dragging: null,
      dragStart: null,
    });
  };

  const handleApplyCrop = () => {
    if (!cropEditor) return;

    // Update the crop in state with adjusted margins
    const { crop, margins } = cropEditor;
    const updatedCrop = {
      ...crop,
      crop_margins: margins,
      needs_recrop: true,
    };

    setUnlabeledCrops((prev) =>
      prev.map((c) => (c.crop_id === crop.crop_id ? updatedCrop : c))
    );

    message.success('裁切调整已保存，标注时将应用调整');
    setCropEditor(null);
  };

  const handleExportModel = async () => {
    try {
      // Use default export path in production/card_recognition/
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const exportPath = `../card_recognition/exports/model_${timestamp}.zip`;
      const result = await api.exportModel(exportPath);
      message.success(`模型已导出: ${result.export_path}`);
    } catch (error) {
      message.error('导出失败: ' + error);
    }
  };

  const handleImportModel = async () => {
    // For now, use a hardcoded path - in real app, use file picker
    try {
      const importPath = prompt('请输入模型文件路径 (ZIP):');
      if (!importPath) return;

      const result = await api.importModel(importPath);
      message.success(`模型已导入: ${result.trained_cards.length} 张卡牌`);
      // Refresh model status
      const status = await api.getModelStatus();
      setModelStatus(status);
    } catch (error) {
      message.error('导入失败: ' + error);
    }
  };

  useEffect(() => {
    // handle recognize image
    handleDetectCards();
  }, [currentImageUrl, screenshotFiles]);

  return (
    <div className={styles.screenshot}>
      <div className={styles.header}>
        <Button
          type='primary'
          onClick={handleCapture}
          loading={loading}
          disabled={!activeWindow}
        >
          捕获截图
        </Button>
      </div>

      <div className={styles.content}>
        <div className={styles.imagePreview}>
          {/* Screenshot file browser */}
          <ImageBrowser
            files={screenshotFiles}
            selectedIndex={selectedFileIndex}
            onSelectFile={handleSelectFile}
            onPrevious={handlePrevious}
            onNext={handleNext}
            disabled={loading || cropMode !== 'browse'}
          />

          {/* Image preview with optional crop editor */}
          <div className={styles.previewContainer}>
            {loading ? (
              <Spin tip='正在加载...' />
            ) : currentImageUrl && imageSize ? (
              <>
                {cropMode === 'cropping' ? (
                  <CropEditor
                    imageUrl={currentImageUrl}
                    imageSize={imageSize}
                    boxes={cropBoxes}
                    onBoxesChange={setCropBoxes}
                  />
                ) : (
                  <Image
                    src={currentImageUrl}
                    alt='Screenshot'
                    preview={false}
                  />
                )}
              </>
            ) : (
              <Empty description='暂无截图，请先捕获截图' />
            )}
          </div>

          {/* Crop mode actions */}
          {currentImageUrl && cropMode === 'browse' && (
            <div style={{ marginTop: '12px', textAlign: 'center' }}>
              <Button type='primary' onClick={handleStartLabeling}>
                开始标注
              </Button>
            </div>
          )}
          {cropMode === 'cropping' && (
            <div style={{ marginTop: '12px', textAlign: 'center' }}>
              <Button
                type='primary'
                onClick={handleFinishCropping}
                loading={loading}
              >
                完成裁切
              </Button>
            </div>
          )}

          {/* Crop labeling section */}
          {cropMode === 'labeling' && extractedCrops.length > 0 && (
            <CropLabeler
              crops={extractedCrops}
              labels={cropLabels}
              cardNames={cardNames}
              onLabelsChange={setCropLabels}
              onSave={handleSaveLabels}
              onCancel={handleCancelLabeling}
              saving={savingLabels}
            />
          )}
        </div>

        {/* Card Detection Section */}
        <div className={styles.cardDetection}>
          <div className={styles.header}>
            <div className={styles.info}>
              {modelStatus && (
                <span className={styles.infoText}>
                  模型已训练: {modelStatus.trained_cards?.length || 0}张 | 样本:{' '}
                  {modelStatus.total_samples || 0}个
                </span>
              )}
            </div>
            <div>
              <Button
                onClick={handleBatchTrain}
                size='small'
                style={{ marginRight: '8px' }}
                loading={loading}
              >
                批量训练
              </Button>
              <Button
                onClick={handleFetchUnlabeled}
                size='small'
                style={{ marginRight: '8px' }}
                loading={loading}
              >
                查看未标注
              </Button>
              <Button
                onClick={handleExportModel}
                size='small'
                style={{ marginRight: '8px' }}
              >
                导出模型
              </Button>
              <Button
                onClick={handleImportModel}
                size='small'
                style={{ marginRight: '8px' }}
              >
                导入模型
              </Button>
              <Button
                onClick={handleTrainModel}
                size='small'
                style={{ marginRight: '8px' }}
              >
                重训
              </Button>
              <Button
                type='primary'
                onClick={handleDetectCards}
                loading={detectingCards}
                disabled={!currentImageUrl && !activeWindow}
                size='small'
              >
                识别
              </Button>
            </div>
          </div>

          {detectionResult && (
            <div className={styles.slotsGrid}>
              {detectionResult.slots.map((slot: any) => (
                <div key={slot.slot_idx} className={styles.slotCard}>
                  <div className={styles.slotLabel}>槽位 {slot.slot_idx}</div>
                  {slot.card === 'unknown' ? (
                    <div className={styles.unknownCard}>
                      <div className={styles.unknownText}>未知</div>
                      <div className={styles.topGuesses}>
                        {slot.top_k_guesses
                          ?.slice(0, 3)
                          .map((guess: string, i: number) => (
                            <div key={i}>
                              {i + 1}. {guess}
                            </div>
                          ))}
                      </div>
                      <Select
                        size='small'
                        style={{ width: '100%' }}
                        placeholder='选择卡牌'
                        onChange={(value) =>
                          handleLabelCard(slot.crop_id, value)
                        }
                        showSearch
                      >
                        {cardNames.map((card: string) => (
                          <Select.Option key={card} value={card}>
                            {card}
                          </Select.Option>
                        ))}
                      </Select>
                    </div>
                  ) : (
                    <div className={styles.knownCard}>
                      <div className={styles.cardName}>{slot.card}</div>
                      <div className={styles.confidence}>
                        {(slot.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        {/* Unlabeled Crops Section */}
        {showUnlabeled && unlabeledCrops.length > 0 && (
          <div className={styles.unlabeledSection}>
            <div className={styles.header}>
              <span className={styles.infoText}>
                未标注卡牌 ({unlabeledCrops.length} 个)
              </span>
              <Button size='small' onClick={() => setShowUnlabeled(false)}>
                隐藏
              </Button>
            </div>
            <div className={styles.unlabeledGrid}>
              {unlabeledCrops.map((crop: any) => (
                <div key={crop.crop_id} className={styles.unlabeledCard}>
                  <img
                    src={crop.image_url}
                    alt={crop.crop_id}
                    className={styles.cropImage}
                  />
                  <div className={styles.cropInfo}>
                    <div className={styles.cropId}>{crop.crop_id}</div>
                    {crop.source && (
                      <div className={styles.cropSource}>
                        来源: {crop.source}
                      </div>
                    )}
                  </div>
                  <div className={styles.cropActions}>
                    <Button
                      size='small'
                      style={{ marginTop: '8px', width: '100%' }}
                      onClick={() => handleOpenCropEditor(crop)}
                    >
                      裁切调整
                    </Button>
                    <Select
                      size='small'
                      style={{ width: '100%', marginTop: '8px' }}
                      placeholder='选择卡牌'
                      onChange={(value) =>
                        handleLabelUnlabeledCard(crop.crop_id, value)
                      }
                      showSearch
                    >
                      {cardNames.map((card: string) => (
                        <Select.Option key={card} value={card}>
                          {card}
                        </Select.Option>
                      ))}
                    </Select>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Crop Editor Modal */}
        {cropEditor && (
          <Modal
            title='裁切调整'
            open={cropEditor.visible}
            onOk={handleApplyCrop}
            onCancel={() => setCropEditor(null)}
            width={700}
          >
            <div style={{ padding: '20px 0', textAlign: 'center' }}>
              <p style={{ marginBottom: '10px', color: '#666' }}>
                拖动红色边框调整裁切区域
              </p>
              <div
                style={{
                  position: 'relative',
                  display: 'inline-block',
                  cursor: cropEditor.dragging ? 'grabbing' : 'default',
                }}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              >
                {/* Background dimmed image */}
                <img
                  id='cropEditorImage'
                  src={cropEditor.crop.image_url}
                  alt='crop preview'
                  style={{
                    maxWidth: '600px',
                    maxHeight: '400px',
                    display: 'block',
                    opacity: 0.3,
                  }}
                />
                {/* Cropped region overlay */}
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    overflow: 'hidden',
                    pointerEvents: 'none',
                  }}
                >
                  <img
                    src={cropEditor.crop.image_url}
                    alt='cropped'
                    style={{
                      maxWidth: '600px',
                      maxHeight: '400px',
                      display: 'block',
                      clipPath: `inset(
                        ${(cropEditor.margins.top / cropEditor.imageSize.height) * 100}% 
                        ${(cropEditor.margins.right / cropEditor.imageSize.width) * 100}% 
                        ${(cropEditor.margins.bottom / cropEditor.imageSize.height) * 100}% 
                        ${(cropEditor.margins.left / cropEditor.imageSize.width) * 100}%
                      )`,
                    }}
                  />
                </div>
                {/* Top border */}
                <div
                  onMouseDown={(e) => handleBorderMouseDown('top', e)}
                  style={{
                    position: 'absolute',
                    top: `${(cropEditor.margins.top / cropEditor.imageSize.height) * 100}%`,
                    left: `${(cropEditor.margins.left / cropEditor.imageSize.width) * 100}%`,
                    right: `${(cropEditor.margins.right / cropEditor.imageSize.width) * 100}%`,
                    height: '3px',
                    backgroundColor: '#ff4d4f',
                    cursor: 'ns-resize',
                    pointerEvents: 'all',
                    zIndex: 10,
                  }}
                />
                {/* Bottom border */}
                <div
                  onMouseDown={(e) => handleBorderMouseDown('bottom', e)}
                  style={{
                    position: 'absolute',
                    bottom: `${(cropEditor.margins.bottom / cropEditor.imageSize.height) * 100}%`,
                    left: `${(cropEditor.margins.left / cropEditor.imageSize.width) * 100}%`,
                    right: `${(cropEditor.margins.right / cropEditor.imageSize.width) * 100}%`,
                    height: '3px',
                    backgroundColor: '#ff4d4f',
                    cursor: 'ns-resize',
                    pointerEvents: 'all',
                    zIndex: 10,
                  }}
                />
                {/* Left border */}
                <div
                  onMouseDown={(e) => handleBorderMouseDown('left', e)}
                  style={{
                    position: 'absolute',
                    top: `${(cropEditor.margins.top / cropEditor.imageSize.height) * 100}%`,
                    bottom: `${(cropEditor.margins.bottom / cropEditor.imageSize.height) * 100}%`,
                    left: `${(cropEditor.margins.left / cropEditor.imageSize.width) * 100}%`,
                    width: '3px',
                    backgroundColor: '#ff4d4f',
                    cursor: 'ew-resize',
                    pointerEvents: 'all',
                    zIndex: 10,
                  }}
                />
                {/* Right border */}
                <div
                  onMouseDown={(e) => handleBorderMouseDown('right', e)}
                  style={{
                    position: 'absolute',
                    top: `${(cropEditor.margins.top / cropEditor.imageSize.height) * 100}%`,
                    bottom: `${(cropEditor.margins.bottom / cropEditor.imageSize.height) * 100}%`,
                    right: `${(cropEditor.margins.right / cropEditor.imageSize.width) * 100}%`,
                    width: '3px',
                    backgroundColor: '#ff4d4f',
                    cursor: 'ew-resize',
                    pointerEvents: 'all',
                    zIndex: 10,
                  }}
                />
              </div>
              <div
                style={{ marginTop: '16px', fontSize: '12px', color: '#999' }}
              >
                裁切边距: 上={cropEditor.margins.top}px, 下=
                {cropEditor.margins.bottom}px, 左={cropEditor.margins.left}px,
                右={cropEditor.margins.right}px
              </div>
            </div>
          </Modal>
        )}
      </div>
    </div>
  );
};

export default ScreenshotContent;

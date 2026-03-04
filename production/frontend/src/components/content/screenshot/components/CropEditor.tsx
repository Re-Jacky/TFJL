import React, { useState, useRef, useEffect } from 'react';
import styles from './CropEditor.module.scss';

export interface CropBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface CropEditorProps {
  imageUrl: string;
  imageSize: { width: number; height: number };
  boxes: CropBox[];
  // eslint-disable-next-line no-unused-vars
  onBoxesChange: (_boxes: CropBox[]) => void;
}

type DragHandle =
  | 'body'
  | 'top'
  | 'bottom'
  | 'left'
  | 'right'
  | 'tl'
  | 'tr'
  | 'bl'
  | 'br';

const CropEditor: React.FC<CropEditorProps> = ({
  imageUrl,
  imageSize,
  boxes,
  onBoxesChange,
}) => {
  const [dragging, setDragging] = useState<{
    boxIndex: number;
    handle: DragHandle;
  } | null>(null);
  const [dragStart, setDragStart] = useState<{
    x: number;
    y: number;
    boxState: CropBox;
  } | null>(null);
  const [scale, setScale] = useState({ scaleX: 1, scaleY: 1 });
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  // Calculate scale when image loads
  useEffect(() => {
    if (imgRef.current) {
      const displayWidth = imgRef.current.clientWidth;
      const displayHeight = imgRef.current.clientHeight;
      setScale({
        scaleX: imageSize.width / displayWidth,
        scaleY: imageSize.height / displayHeight,
      });
    }
  }, [imageUrl, imageSize]);

  const handleMouseDown = (
    boxIndex: number,
    handle: DragHandle,
    e: React.MouseEvent
  ) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging({ boxIndex, handle });
    setDragStart({
      x: e.clientX,
      y: e.clientY,
      boxState: { ...boxes[boxIndex] },
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragging || !dragStart) return;

    const deltaX = (e.clientX - dragStart.x) * scale.scaleX;
    const deltaY = (e.clientY - dragStart.y) * scale.scaleY;

    const newBox = { ...dragStart.boxState };
    const { handle } = dragging;

    if (handle === 'body') {
      // Move entire box
      newBox.x = Math.max(
        0,
        Math.min(imageSize.width - newBox.w, dragStart.boxState.x + deltaX)
      );
      newBox.y = Math.max(
        0,
        Math.min(imageSize.height - newBox.h, dragStart.boxState.y + deltaY)
      );
    } else if (handle === 'top') {
      const newY = Math.max(0, dragStart.boxState.y + deltaY);
      newBox.h = Math.max(
        10,
        dragStart.boxState.h + (dragStart.boxState.y - newY)
      );
      newBox.y = newY;
    } else if (handle === 'bottom') {
      newBox.h = Math.max(
        10,
        Math.min(imageSize.height - newBox.y, dragStart.boxState.h + deltaY)
      );
    } else if (handle === 'left') {
      const newX = Math.max(0, dragStart.boxState.x + deltaX);
      newBox.w = Math.max(
        10,
        dragStart.boxState.w + (dragStart.boxState.x - newX)
      );
      newBox.x = newX;
    } else if (handle === 'right') {
      newBox.w = Math.max(
        10,
        Math.min(imageSize.width - newBox.x, dragStart.boxState.w + deltaX)
      );
    } else if (handle === 'tl') {
      const newX = Math.max(0, dragStart.boxState.x + deltaX);
      const newY = Math.max(0, dragStart.boxState.y + deltaY);
      newBox.w = Math.max(
        10,
        dragStart.boxState.w + (dragStart.boxState.x - newX)
      );
      newBox.h = Math.max(
        10,
        dragStart.boxState.h + (dragStart.boxState.y - newY)
      );
      newBox.x = newX;
      newBox.y = newY;
    } else if (handle === 'tr') {
      const newY = Math.max(0, dragStart.boxState.y + deltaY);
      newBox.w = Math.max(
        10,
        Math.min(imageSize.width - newBox.x, dragStart.boxState.w + deltaX)
      );
      newBox.h = Math.max(
        10,
        dragStart.boxState.h + (dragStart.boxState.y - newY)
      );
      newBox.y = newY;
    } else if (handle === 'bl') {
      const newX = Math.max(0, dragStart.boxState.x + deltaX);
      newBox.w = Math.max(
        10,
        dragStart.boxState.w + (dragStart.boxState.x - newX)
      );
      newBox.h = Math.max(
        10,
        Math.min(imageSize.height - newBox.y, dragStart.boxState.h + deltaY)
      );
      newBox.x = newX;
    } else if (handle === 'br') {
      newBox.w = Math.max(
        10,
        Math.min(imageSize.width - newBox.x, dragStart.boxState.w + deltaX)
      );
      newBox.h = Math.max(
        10,
        Math.min(imageSize.height - newBox.y, dragStart.boxState.h + deltaY)
      );
    }

    const newBoxes = [...boxes];
    newBoxes[dragging.boxIndex] = newBox;
    onBoxesChange(newBoxes);
  };

  const handleMouseUp = () => {
    setDragging(null);
    setDragStart(null);
  };

  const renderBox = (box: CropBox, index: number) => {
    const displayX = box.x / scale.scaleX;
    const displayY = box.y / scale.scaleY;
    const displayW = box.w / scale.scaleX;
    const displayH = box.h / scale.scaleY;

    return (
      <div key={index} className={styles.cropBox}>
        {/* Main box */}
        <div
          className={styles.boxBorder}
          style={{
            left: `${displayX}px`,
            top: `${displayY}px`,
            width: `${displayW}px`,
            height: `${displayH}px`,
          }}
          onMouseDown={(e) => handleMouseDown(index, 'body', e)}
        >
          {/* Box number label */}
          <div className={styles.boxLabel}>{index + 1}</div>

          {/* Dimension tooltip */}
          <div className={styles.boxDimensions}>
            {Math.round(box.w)} × {Math.round(box.h)}
          </div>

          {/* Resize handles */}
          <div
            className={`${styles.handle} ${styles.handleTL}`}
            onMouseDown={(e) => handleMouseDown(index, 'tl', e)}
          />
          <div
            className={`${styles.handle} ${styles.handleTR}`}
            onMouseDown={(e) => handleMouseDown(index, 'tr', e)}
          />
          <div
            className={`${styles.handle} ${styles.handleBL}`}
            onMouseDown={(e) => handleMouseDown(index, 'bl', e)}
          />
          <div
            className={`${styles.handle} ${styles.handleBR}`}
            onMouseDown={(e) => handleMouseDown(index, 'br', e)}
          />
          <div
            className={`${styles.handle} ${styles.handleT}`}
            onMouseDown={(e) => handleMouseDown(index, 'top', e)}
          />
          <div
            className={`${styles.handle} ${styles.handleB}`}
            onMouseDown={(e) => handleMouseDown(index, 'bottom', e)}
          />
          <div
            className={`${styles.handle} ${styles.handleL}`}
            onMouseDown={(e) => handleMouseDown(index, 'left', e)}
          />
          <div
            className={`${styles.handle} ${styles.handleR}`}
            onMouseDown={(e) => handleMouseDown(index, 'right', e)}
          />
        </div>
      </div>
    );
  };

  return (
    <div
      ref={containerRef}
      className={styles.cropEditor}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Dimmed background image */}
      <img
        ref={imgRef}
        src={imageUrl}
        alt='Screenshot'
        className={styles.backgroundImage}
        draggable={false}
      />

      {/* Overlay container for boxes */}
      <div className={styles.overlayContainer}>
        {boxes.map((box, index) => renderBox(box, index))}
      </div>
    </div>
  );
};

export default CropEditor;

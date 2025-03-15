import React, { useState } from 'react';
import { Upload, Button, Card, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import axios from 'axios';

const ImageComparison: React.FC = () => {
  const [image1, setImage1] = useState<File | null>(null);
  const [image2, setImage2] = useState<File | null>(null);
  const [similarity, setSimilarity] = useState<number | null>(null);

  const handleCompare = async () => {
    if (!image1 || !image2) {
      message.error('Please upload both images first');
      return;
    }

    const formData = new FormData();
    formData.append('image1', image1);
    formData.append('image2', image2);

    try {
      const response = await axios.post('http://localhost:8000/compare-images', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setSimilarity(response.data.similarity_score);
      message.success('Comparison completed');
    } catch (error) {
      message.error('Error comparing images');
      console.error(error);
    }
  };

  return (
    <Card title="Image Comparison">
      <div style={{ display: 'flex', gap: '20px' }}>
        <Upload
          beforeUpload={(file) => {
            setImage1(file);
            return false;
          }}
          maxCount={1}
        >
          <Button icon={<UploadOutlined />}>Upload Image 1</Button>
        </Upload>

        <Upload
          beforeUpload={(file) => {
            setImage2(file);
            return false;
          }}
          maxCount={1}
        >
          <Button icon={<UploadOutlined />}>Upload Image 2</Button>
        </Upload>

        <Button type="primary" onClick={handleCompare}>
          Compare Images
        </Button>
      </div>

      {similarity !== null && (
        <div style={{ marginTop: '20px' }}>
          <h3>Similarity Score: {(similarity * 100).toFixed(2)}%</h3>
        </div>
      )}
    </Card>
  );
};

export default ImageComparison;
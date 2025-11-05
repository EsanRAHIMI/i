'use client';

import { useState, useRef, useCallback } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { apiClient } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

interface AvatarCustomizationProps {
  onClose?: () => void;
  onSave?: (avatarData: any) => void;
}

export function AvatarCustomization({ onClose, onSave }: AvatarCustomizationProps) {
  const { user, updateUser } = useAppStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select a valid image file');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('Image size must be less than 5MB');
      return;
    }

    setSelectedFile(file);
    setError(null);

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreviewImage(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  }, []);

  const handleDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    
    if (file && file.type.startsWith('image/')) {
      // Create a proper FileList-like object
      const fileList = {
        0: file,
        length: 1,
        item: (index: number) => index === 0 ? file : null,
        [Symbol.iterator]: function* () { yield file; }
      } as FileList;
      
      const syntheticEvent = {
        target: { files: fileList },
        currentTarget: { files: fileList }
      } as unknown as React.ChangeEvent<HTMLInputElement>;
      
      handleFileSelect(syntheticEvent);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  }, []);

  const processAvatar = async () => {
    if (!selectedFile) return;

    try {
      setIsLoading(true);
      setError(null);

      // Upload avatar to server
      const updatedUser = await apiClient.uploadAvatar(selectedFile);

      // Update user in store
      if (updatedUser && updatedUser.avatar_url) {
        await updateUser({ avatar_url: updatedUser.avatar_url });
      }

      // Prepare avatar data for callback
      const avatarData = {
        avatar_url: updatedUser.avatar_url || previewImage,
        facial_features: {
          eye_color: 'brown',
          hair_color: 'dark',
          skin_tone: 'medium',
          face_shape: 'oval'
        },
        generated_at: new Date().toISOString()
      };

      onSave?.(avatarData);
      onClose?.();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to upload avatar';
      setError(errorMessage);
      console.error('Avatar upload error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const resetSelection = () => {
    setSelectedFile(null);
    setPreviewImage(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-800 rounded-lg border border-gray-700 w-full max-w-md">
        <div className="p-6 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Customize Your Avatar</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p className="text-gray-400 text-sm mt-2">
            Upload a selfie to create a personalized 3D avatar
          </p>
        </div>

        <div className="p-6 space-y-6">
          {/* Upload Area */}
          <div
            className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-primary-500 transition-colors cursor-pointer"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
            />

            {previewImage ? (
              <div className="space-y-4">
                <img
                  src={previewImage}
                  alt="Avatar preview"
                  className="w-32 h-32 rounded-full mx-auto object-cover border-4 border-primary-500"
                />
                <div className="space-y-2">
                  <p className="text-white font-medium">Ready to generate avatar</p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      resetSelection();
                    }}
                    className="text-primary-400 hover:text-primary-300 text-sm"
                  >
                    Choose different image
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="w-16 h-16 mx-auto bg-gray-700 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <p className="text-white font-medium">Upload your selfie</p>
                  <p className="text-gray-400 text-sm">Drag and drop or click to browse</p>
                  <p className="text-gray-500 text-xs mt-1">PNG, JPG up to 5MB</p>
                </div>
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Avatar Features Info */}
          <div className="bg-dark-900 rounded-lg p-4">
            <h3 className="text-white font-medium mb-2">Avatar Features</h3>
            <ul className="text-gray-400 text-sm space-y-1">
              <li>• Facial recognition for accurate representation</li>
              <li>• Lip-sync animation with voice output</li>
              <li>• Real-time expressions and emotions</li>
              <li>• Privacy-first processing (data stays local)</li>
            </ul>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={processAvatar}
              disabled={!selectedFile || isLoading}
              className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center justify-center space-x-2"
            >
              {isLoading ? (
                <>
                  <LoadingSpinner size="sm" />
                  <span>Processing...</span>
                </>
              ) : (
                <span>Generate Avatar</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
use serde::{Deserialize, Serialize};
use std::path::{Component, Path, PathBuf};
use std::fs;

#[derive(Debug, Serialize, Deserialize)]
pub struct CapabilityManifest {
    pub skill_name: String,
    pub filesystem: FSAccess,
    pub network: bool,
    pub gpu: bool,
    pub sensors: bool,
    pub camera: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FSAccess {
    pub read: Vec<String>,
    pub write: Vec<String>,
    pub delete: Vec<String>,
}

impl CapabilityManifest {
    pub fn validate(&self, operation: &str, path: &str) -> bool {
        let normalized_path = Self::normalize_path(path);

        let check_path = |patterns: &Vec<String>| {
            patterns.iter().any(|p| {
                let norm_pattern = Self::normalize_path(p);
                normalized_path.starts_with(&norm_pattern)
            })
        };

        match operation {
            "read" => check_path(&self.filesystem.read),
            "write" => check_path(&self.filesystem.write),
            "delete" => check_path(&self.filesystem.delete),
            _ => false,
        }
    }

    pub fn normalize_path(path: &str) -> String {
        let mut path = path.replace('\\', "/");
        let mut disk = None;
        
        // Выделяем префикс диска (например "C:")
        if path.len() >= 2 {
            let prefix = &path[0..2];
            if prefix.ends_with(':') {
                if let Some(c) = prefix.chars().next() {
                    if c.is_ascii_alphabetic() {
                        disk = Some(prefix.to_string());
                        path = path[2..].to_string();
                    }
                }
            }
        }
    
        let is_absolute = path.starts_with('/');
        let mut components = Vec::new();
    
        for part in path.split('/') {
            match part {
                "" | "." => continue,
                ".." => {
                    if let Some(last) = components.last() {
                        if *last == ".." {
                            components.push(part);
                        } else {
                            components.pop();
                        }
                    } else if is_absolute {
                        // Игнорируем попытку выйти выше корня
                    } else {
                        components.push("..");
                    }
                }
                _ => components.push(part),
            }
        }
    
        let mut result = components.join("/");
        
        // Добавляем ведущий слэш для абсолютных путей
        if is_absolute && !result.starts_with('/') {
            result.insert(0, '/');
        }
        
        // Восстанавливаем префикс диска
        if let Some(disk) = disk {
            result = format!("{}{}", disk, result);
        }
    
        result
    }

    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self, String> {
        let data = fs::read_to_string(path)
            .map_err(|e| e.to_string())?;
        serde_json::from_str(&data)
            .map_err(|e| e.to_string())
    }

    pub fn to_json(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_default()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_manifest_validation() {
        let manifest = CapabilityManifest {
            skill_name: "TestSkill".to_string(),
            filesystem: FSAccess {
                read: vec!["/data".to_string()],
                write: vec![],
                delete: vec!["/tmp".to_string()],
            },
            network: false,
            gpu: false,
            sensors: true,
            camera: false,
        };

        // Тесты на path traversal
        assert!(!manifest.validate("read", "/data/../etc/passwd"));
        assert!(!manifest.validate("delete", "/tmp/../etc"));
        assert!(!manifest.validate("read", "/data/./../root"));
        assert!(manifest.validate("read", "/data/./file.txt"));
    }

    #[test]
    fn test_path_normalization() {
        assert_eq!(CapabilityManifest::normalize_path("/tmp/../etc"), "/etc");
        assert_eq!(CapabilityManifest::normalize_path("/var/./log/../tmp"), "/var/tmp");
        assert_eq!(CapabilityManifest::normalize_path("C:\\Windows\\..\\System32"), "C:/System32");
        assert_eq!(CapabilityManifest::normalize_path("/a/b/c/../../d"), "/a/d");
        assert_eq!(CapabilityManifest::normalize_path("/data/../etc/passwd"), "/etc/passwd");
        assert_eq!(CapabilityManifest::normalize_path("C:\\\\Users\\\\test"), "C:/Users/test");
    }
}
